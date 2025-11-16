"""
System Integration Layer
Handles all backend system connections: SSH, StoreMaster, ServiceNow, etc.
Based on CATALINA_AI_VOICE_AGENT_DESIGN.md specifications
"""

import paramiko
import httpx
import asyncio
from typing import Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)


class SystemTools:
    """
    Integrates with Catalina's backend systems
    """
    
    def __init__(self):
        self.ssh_connections = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # API endpoints
        self.storemaster_api = os.getenv("STOREMASTER_API_URL")
        self.servicenow_api = os.getenv("SERVICENOW_API_URL")
        
        # Credentials
        self.ssh_user = os.getenv("STORE_SSH_USER")
        self.ssh_key_path = os.getenv("STORE_SSH_KEY_PATH")
        
    async def execute(self, function_name: str, arguments: Dict) -> Dict:
        """
        Main entry point for executing system tools
        """
        try:
            if function_name == "check_printer_status":
                return await self.check_printer_status(**arguments)
            elif function_name == "send_test_print":
                return await self.send_test_print(**arguments)
            elif function_name == "perform_ink_cleaning":
                return await self.perform_ink_cleaning(**arguments)
            elif function_name == "update_ticket":
                return await self.update_ticket(**arguments)
            elif function_name == "get_store_info":
                return await self.get_store_info(**arguments)
            else:
                raise ValueError(f"Unknown function: {function_name}")
        except Exception as e:
            logger.error(f"Error executing {function_name}: {str(e)}")
            return {"error": str(e), "success": False}
    
    async def check_printer_status(self, chain: int, store: int, lane: int) -> Dict:
        """
        Check printer status via SSH connection
        """
        try:
            connection = await self._get_ssh_connection(chain, store)
            
            # Execute printer status command
            stdin, stdout, stderr = connection.exec_command(
                f'cd /catalina && ./printer_status {lane}'
            )
            
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            if error:
                logger.warning(f"Printer status error: {error}")
            
            # Parse status
            status = self._parse_printer_status(output)
            
            return {
                "success": True,
                "lane": lane,
                "status": status["status"],
                "details": status["details"]
            }
            
        except Exception as e:
            logger.error(f"Failed to check printer status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status": "unknown"
            }
    
    async def send_test_print(self, chain: int, store: int, lane: int) -> Dict:
        """
        Send test coupon to printer
        """
        try:
            connection = await self._get_ssh_connection(chain, store)
            
            # Execute test print command
            stdin, stdout, stderr = connection.exec_command(
                f'cd /catalina && coup {lane}'
            )
            
            output = stdout.read().decode('utf-8')
            
            return {
                "success": "sent" in output.lower() or "success" in output.lower(),
                "message": "Test coupon sent",
                "output": output.strip()
            }
            
        except Exception as e:
            logger.error(f"Failed to send test print: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def perform_ink_cleaning(self, chain: int, store: int, lane: int) -> Dict:
        """
        Perform remote ink cleaning
        """
        try:
            connection = await self._get_ssh_connection(chain, store)
            
            # Execute ink cleaning command
            stdin, stdout, stderr = connection.exec_command(
                f'cd /catalina && ink_clean {lane}'
            )
            
            output = stdout.read().decode('utf-8')
            
            # Cleaning takes ~60 seconds
            await asyncio.sleep(2)  # Wait a bit for command to initiate
            
            return {
                "success": True,
                "message": "Ink cleaning initiated",
                "estimated_duration": 60
            }
            
        except Exception as e:
            logger.error(f"Failed to perform ink cleaning: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_ticket(self, ticket_id: str, status: str, 
                           resolution_notes: str, **kwargs) -> Dict:
        """
        Update ServiceNow ticket
        """
        try:
            if not self.servicenow_api:
                logger.warning("ServiceNow API not configured")
                return {
                    "success": False,
                    "error": "ServiceNow API not configured"
                }
            
            response = await self.http_client.patch(
                f"{self.servicenow_api}/api/now/table/incident/{ticket_id}",
                headers={
                    "Authorization": f"Bearer {os.getenv('SERVICENOW_TOKEN')}",
                    "Content-Type": "application/json"
                },
                json={
                    "state": self._map_status_to_servicenow(status),
                    "work_notes": resolution_notes,
                    **kwargs
                }
            )
            
            return {
                "success": response.status_code == 200,
                "ticket_id": ticket_id
            }
            
        except Exception as e:
            logger.error(f"Failed to update ticket: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_store_info(self, chain: int, store: int) -> Dict:
        """
        Get store information from StoreMaster
        """
        try:
            if not self.storemaster_api:
                logger.warning("StoreMaster API not configured")
                return {
                    "success": False,
                    "error": "StoreMaster API not configured"
                }
            
            response = await self.http_client.get(
                f"{self.storemaster_api}/stores/{chain}/{store}",
                headers={"Authorization": f"Bearer {os.getenv('STOREMASTER_TOKEN')}"}
            )
            
            return {
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get store info: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_ssh_connection(self, chain: int, store: int) -> paramiko.SSHClient:
        """
        Get or create SSH connection to store
        """
        connection_key = f"{chain}-{store}"
        
        if connection_key in self.ssh_connections:
            # Check if connection is still alive
            try:
                transport = self.ssh_connections[connection_key].get_transport()
                if transport and transport.is_active():
                    return self.ssh_connections[connection_key]
            except:
                pass
        
        # Create new connection
        store_info = await self._get_store_info(chain, store)
        
        if not store_info.get("success") or not store_info.get("data"):
            raise ConnectionError(f"Could not retrieve store info for chain {chain}, store {store}")
        
        store_data = store_info["data"]
        ip_address = store_data.get("ip_address") or f"store-{chain}-{store}.catalina.internal"
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if self.ssh_key_path:
            client.connect(
                hostname=ip_address,
                username=self.ssh_user,
                key_filename=self.ssh_key_path
            )
        else:
            client.connect(
                hostname=ip_address,
                username=self.ssh_user,
                password=os.getenv("STORE_SSH_PASSWORD")
            )
        
        self.ssh_connections[connection_key] = client
        return client
    
    async def _get_store_info(self, chain: int, store: int) -> Dict:
        """
        Get store information from StoreMaster (internal method)
        """
        return await self.get_store_info(chain, store)
    
    def _parse_printer_status(self, output: str) -> Dict:
        """
        Parse printer status command output
        """
        status_map = {
            "Idle": "ready",
            "ready": "ready",
            "Busy": "busy",
            "Off Line": "offline",
            "offline": "offline",
            "Error": "error",
            "Paper Jam": "error",
            "Out of Ink": "out_of_ink",
            "Out of Paper": "out_of_paper"
        }
        
        output_lower = output.lower()
        
        for key, value in status_map.items():
            if key.lower() in output_lower:
                return {
                    "status": value,
                    "details": output.strip()
                }
        
        return {
            "status": "unknown",
            "details": output.strip()
        }
    
    def _map_status_to_servicenow(self, status: str) -> str:
        """
        Map our status to ServiceNow state values
        """
        status_map = {
            "resolved": "6",  # Resolved
            "escalated": "2",  # In Progress
            "in_progress": "2"
        }
        return status_map.get(status, "2")
    
    async def close(self):
        """
        Close all connections
        """
        for connection in self.ssh_connections.values():
            try:
                connection.close()
            except:
                pass
        
        await self.http_client.aclose()

