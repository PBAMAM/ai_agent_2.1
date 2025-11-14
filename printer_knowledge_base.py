"""
Printer Knowledge Base - Contains printer issue types, resolutions, and detailed troubleshooting steps
Based on Catalina documentation for printer troubleshooting
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class PrinterIssue:
    """Represents a printer issue with its resolution and related information"""
    system_alert_type: str  # Outbound system alert issue type
    caller_issue_type: str  # Inbound caller issue type
    resolution: str
    impacted_equipment: str
    call_recording_needed: bool
    call_recording_id: Optional[str] = None
    detailed_steps: Optional[List[str]] = None
    special_notes: Optional[List[str]] = None


class PrinterKnowledgeBase:
    """Knowledge base for printer issues and resolutions with detailed troubleshooting steps"""
    
    def __init__(self):
        self.issues: List[PrinterIssue] = [
            PrinterIssue(
                system_alert_type="Mech Error / Paper Out",
                caller_issue_type="Printer Making Sounds / Paper not coming out",
                resolution="Loaded Paper",
                impacted_equipment="CMC6",
                call_recording_needed=True,
                call_recording_id="CALL 1",
                detailed_steps=[
                    "Call the store and let them know the printer on their lane is showing out of paper",
                    "Ask if they can put in a new roll of paper",
                    "If they need help, guide them: put the paper in with the letter side facing down, feed it through the top of the paper door, then close the door",
                    "If the store is out of paper, note that in the ticket and follow up on paper delivery",
                    "Once paper is loaded, check that the printer shows ready status",
                    "Send a test print to verify everything is working",
                    "If the print quality looks good, you're all set! If not, you may need to run an ink cleaning"
                ],
                special_notes=[
                    "FOR PRINTER OUTBOUND CALLS (SYSTEM ALERTS OR NON-POOR PRINT MAIL LISTEN TICKETS), AGENTS ARE NO LONGER REQUIRED TO SEND OR OFFER TO SEND TEST COUP(S) AFTER FIXING THE ISSUE. A TEST COUP WILL ONLY BE SENT AS PER POC'S Request"
                ]
            ),
            PrinterIssue(
                system_alert_type="Mech Error",
                caller_issue_type="Printer Making Sounds / Paper not coming out",
                resolution="Cleared Paper Jam",
                impacted_equipment="CMC6",
                call_recording_needed=True,
                call_recording_id="CALL 2",
                detailed_steps=[
                    "Call the store and help them clear the paper jam",
                    "Have them open the paper door and remove the paper roll",
                    "Ask them to tilt the printer so you can see inside - check for any stuck paper in the front upper corners",
                    "For CMC6 printers: look for a small silver square metal plate (the print head) on the inside top part",
                    "Have them gently move the print head to the right and remove any debris that's stuck",
                    "Important: Don't use compressed air on the printer",
                    "Put the paper roll back in, close the door, and press the reset button on the bottom left",
                    "Wait about 30 seconds for the printer to reset",
                    "Check that the printer shows ready, then send a test print",
                    "If the print quality looks good, you're done! If not, you may need to run an ink cleaning"
                ],
                special_notes=[
                    "FOR PRINTER OUTBOUND CALLS (SYSTEM ALERTS OR NON-POOR PRINT MAIL LISTEN TICKETS), AGENTS ARE NO LONGER REQUIRED TO SEND OR OFFER TO SEND TEST COUP(S) AFTER FIXING THE ISSUE",
                    "FOLLOW STANDARD POC UNWILLING PROCESS: L1C POC Unwilling to Assist",
                    "IF POC IS INSISTENT IN SENDING A TECH RIGHT AWAY: Agents need to escalate to a SME if a non-flagship store is demanding dispatch"
                ]
            ),
            PrinterIssue(
                system_alert_type="Ink Out / NR Error",
                caller_issue_type="Printer Making Sounds / Error light on printer / poor print quality / Blank Prints",
                resolution="Loaded Ink",
                impacted_equipment="CMC6",
                call_recording_needed=True,
                call_recording_id="CALL 3",
                detailed_steps=[
                    "Call the store and ask if they have a new, unopened ink cartridge available",
                    "If yes, have them remove the old cartridge and open a fresh one from the sealed package while you're on the phone",
                    "For CMC9 cartridges, they're in a brown box with bright yellow Catalina labels",
                    "Install the new cartridge and close the ink door",
                    "The printer will automatically run a cleaning cycle (about 60 seconds) - the status light will flash",
                    "If the new cartridge doesn't work, try one from a working printer to test if it's a bad cartridge",
                    "If the store is out of ink, note that in the ticket and check on ink delivery status",
                    "Once the ink is replaced, check that the printer shows ready",
                    "Send a test print to verify everything is working",
                    "If the print quality looks good, you're all set! If not, you may need to run an ink cleaning"
                ],
                special_notes=[
                    "Reasons why some cartridges will not work:",
                    "- The cartridge is defective",
                    "- POC tried an old cartridge that may have been sitting in the ink box, possibly in an open wrapper",
                    "- POC took a cartridge from another printer",
                    "- Sometimes on install of a cartridge, the printer does an ink cleaning which may have depleted the rest of the ink",
                    "- POC thinks the cartridge is full since it feels and sounds like there is plenty of ink in it",
                    "- The cartridges have multiple colors, and if one color runs out, it no longer prints any color",
                    "- The cartridges have a well for spent ink that's used during ink cleanings, and that will make the cartridge seem full"
                ]
            ),
            PrinterIssue(
                system_alert_type="NR Error",
                caller_issue_type="poor print quality / Blank Prints",
                resolution="Ink Cleaning",
                impacted_equipment="CMC6",
                call_recording_needed=True,
                call_recording_id="CALL 4",
                detailed_steps=[
                    "For Walgreens Mail Listen tickets, run an ink cleaning cycle before calling and send the ink cleaning email",
                    "Let the store know you'll be doing a full remote ink cleaning",
                    "If the printer beeps for no ink, have them replace it with a new cartridge from a sealed package",
                    "If it beeps for no paper, have them replace it with a new roll",
                    "Don't worry if blank paper comes out during cleaning - that's normal, just check the final test print with the barcode",
                    "After the cleaning cycle completes, check the print quality",
                    "If the print quality looks good, you're done!",
                    "If it's still not good, you may need to order a replacement printer or dispatch a tech depending on the printer model"
                ],
                special_notes=[
                    "CMC6 Ink Cleaning",
                    "For Kroger Chains: Blank coupon - Dispatch to replace the Printer if the issue happens again for the same printer",
                    "For Kroger Chains: Poor Print - Do not dispatch if the issue is resolved remotely"
                ]
            ),
            PrinterIssue(
                system_alert_type="PC No Comm",
                caller_issue_type="Store not printing / Promos not printing",
                resolution="PC Reboot",
                impacted_equipment="CMC6",
                call_recording_needed=True,
                call_recording_id="CALL 5",
                detailed_steps=[
                    "Try connecting to the store first - if it connects, check the store vitals",
                    "If you can't connect, call the store and let them know you need help checking the Catalina PC",
                    "The PC looks like a regular desktop computer tower with a blue & white 'Property of Catalina Marketing' sticker",
                    "It usually has a monitor and keyboard attached - most stores use a 9-inch TVS monitor",
                    "Use the storemaster list to find the PC details if needed",
                    "Have them reboot the PC: press and hold the power button until it turns off, wait 45-60 seconds, then press it again to turn it back on",
                    "Check if the PC has power - look for a green light on the tower and see what's on the monitor",
                    "If there's no power, have them check the power cord connections and that the outlet works",
                    "Try connecting to the store again after the reboot",
                    "If it still won't connect after 2-3 minutes, you'll need to dispatch a tech to reload the software",
                    "If the PC gives boot options, select Linux. If it goes to Emergency Mode or won't boot properly, dispatch a tech",
                    "Once connected, check the store vitals - if everything looks good, you're done!"
                ],
                special_notes=[
                    "For WAGs Mail Listen tickets opened for a Printer issue but showing No Comm, the agent needs to defer and reconnect after 30 minutes to check the PC's connectivity",
                    "If the PC is still No Comm AND the Incident Request/Description Field states 'Poor Print Quality/Printing Blank Printer', then:",
                    "- Add to the Tech Special Instructions: 'Please attempt to resolve Poor Print Issue on TID XX.'",
                    "- Move the ticket to the US_L1_FSV_BREAKFIX queue",
                    "- Click the dispatch equipment button and click save"
                ]
            ),
            PrinterIssue(
                system_alert_type="NR Error",
                caller_issue_type="Printer Wont Power On / Printer not Printing / Promo not printing",
                resolution="Plugged-in Printer Power Cord",
                impacted_equipment="CMC6",
                call_recording_needed=True,
                call_recording_id="CALL 6",
                detailed_steps=[
                    "Ask them to check the lights on the front of the printer - is the power light solid green, blinking, or off?",
                    "Also have them check the lights on the printer server (the small box on the back) - the Ethernet, Status, and USB lights should be green (the wireless light is always blank)",
                    "If the power light is solid green: have them remove the back cover and tell you the color of each light on the printer server",
                    "If the power light is blinking: have them press and hold the reset button until paper advances, then try pinging the printer",
                    "If the power light is off: check if the lane has power first, then have them check the power cable connection in the bottom right corner",
                    "To power cycle the printer: disconnect the power cord for 30 seconds (you may need to disconnect the USB and printer server wires first to access it)",
                    "Reconnect all the wires - the power cord has an arrow on the flat side that should face outward",
                    "Reseat the Ethernet and printer server wires on the printer server box",
                    "Check all the lights again - they should all be green",
                    "If any light is red, have them disconnect and reconnect that cable (Ethernet or USB) - it should turn orange then green",
                    "If the printer still won't respond after all this, you may need to restart the service or dispatch",
                    "If the printer shows an error (like a paper jam), follow the paper jam clearing steps"
                ],
                special_notes=[
                    "For all 'No Response' tickets, the POC must always be instructed to remove the back cover of the printer and confirm that all five wires are fully plugged into the ports on the back of the printer",
                    "For HEB Stores (Chain 214): Refer to special handling note",
                    "Agent must log into Putty and verify the printer status",
                    "If printer status shows 'Error,' refer to Section 5"
                ]
            ),
            PrinterIssue(
                system_alert_type="Printer Shows Offline (But Firmware Good)",
                caller_issue_type="Printer Not Printing",
                resolution="Printer SW - Not Commable (Restart Services)",
                impacted_equipment="CMC6",
                call_recording_needed=True,
                call_recording_id="CALL 7",
                detailed_steps=[
                    "Log into Putty and check the printer status",
                    "If the printer shows as working in Putty but still shows offline in the system, close the ticket and email the Customer Service Desk that the Store Master List didn't update",
                    "Printer status meanings:",
                    "  - Idle = ready to print",
                    "  - Busy = printing or cleaning",
                    "  - Offline = power or ethernet cable likely unplugged",
                    "  - Error = likely a paper jam or mechanical issue",
                    "To send a test print, type 'Coup <Lane#>' and press enter",
                    "If the printer is still offline after troubleshooting, you may need to order a replacement or dispatch a tech depending on the printer model"
                ],
                special_notes=[
                    "DO NOT TOUCH/Rework Tickets: Agents are instructed not to touch or rework tickets that have specific notes in the Resolution field",
                    "When a ticket is due for closure, dispatch, or escalation, any notes related to these actions should be removed from the Resolution field if they are no longer applicable",
                    "See Store 3.0 Agents Special Instructions for further guidance"
                ]
            ),
        ]
    
    def search_by_caller_description(self, description: str) -> List[PrinterIssue]:
        """
        Search for printer issues by caller's description of the problem.
        Returns matching issues ordered by relevance.
        """
        description_lower = description.lower()
        matches = []
        
        for issue in self.issues:
            score = 0
            caller_issue_lower = issue.caller_issue_type.lower()
            
            # Check for keyword matches
            keywords = description_lower.split()
            for keyword in keywords:
                if len(keyword) > 3:  # Ignore short words
                    if keyword in caller_issue_lower:
                        score += 1
            
            # Check for common phrases
            common_phrases = [
                "paper", "ink", "printing", "error", "offline", 
                "power", "sound", "quality", "blank", "promo", "jam",
                "mechanical", "no response", "not printing", "wont power"
            ]
            for phrase in common_phrases:
                if phrase in description_lower and phrase in caller_issue_lower:
                    score += 2
            
            if score > 0:
                matches.append((score, issue))
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x[0], reverse=True)
        return [issue for _, issue in matches]
    
    def search_by_system_alert(self, alert_type: str) -> List[PrinterIssue]:
        """Search for printer issues by system alert type"""
        alert_lower = alert_type.lower()
        matches = []
        
        for issue in self.issues:
            if alert_lower in issue.system_alert_type.lower() or issue.system_alert_type.lower() in alert_lower:
                matches.append(issue)
        
        return matches
    
    def get_all_issues(self) -> List[PrinterIssue]:
        """Get all printer issues"""
        return self.issues
    
    def get_resolution_steps(self, issue: PrinterIssue) -> List[str]:
        """Get detailed resolution steps for an issue"""
        if issue.detailed_steps:
            return issue.detailed_steps
        
        # Fallback to basic steps if detailed_steps not available
        resolution_steps = {
            "Loaded Paper": [
                "Open the paper tray and check if paper is loaded correctly",
                "Make sure the paper is aligned properly",
                "Close the tray and send a test print to verify it's working"
            ],
            "Cleared Paper Jam": [
                "Turn off the printer and open all access panels",
                "Gently remove any jammed paper and check for torn pieces",
                "Close all panels, turn the printer back on, and test print"
            ],
            "Loaded Ink": [
                "Open the ink cartridge door and remove the old cartridge",
                "Install the new cartridge making sure it's seated properly",
                "Close the door and let the printer run its cleaning cycle",
                "Send a test print to verify everything is working"
            ],
            "Ink Cleaning": [
                "Access the printer maintenance menu",
                "Select the ink cleaning option and follow the prompts",
                "Wait for the cleaning cycle to finish, then test print"
            ],
            "PC Reboot": [
                "Restart the PC and wait for it to fully boot up",
                "Check that the printer connection is working",
                "Send a test print to verify everything is resolved"
            ],
            "Plugged-in Printer Power Cord": [
                "Check that the power cord is connected to both the printer and the outlet",
                "Make sure the outlet has power and the printer switch is on",
                "Test that the printer powers on correctly"
            ],
            "Printer SW - Not Commable (Restart Services)": [
                "Access the printer service settings",
                "Restart the printer service and wait a moment",
                "Check that the service is running and the printer is connected",
                "Send a test print to verify everything is working"
            ]
        }
        
        return resolution_steps.get(issue.resolution, [
            f"Follow the resolution steps for: {issue.resolution}"
        ])
