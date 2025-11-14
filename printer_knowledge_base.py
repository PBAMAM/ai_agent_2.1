"""
Printer Knowledge Base - Contains printer issue types, resolutions, and detailed KBAs
Based on Catalina KBA documentation for printer troubleshooting
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
    kba: str  # Knowledge Base Article number
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
                kba="KBA3813",
                call_recording_needed=True,
                call_recording_id="CALL 1",
                detailed_steps=[
                    "1. Ensure Diagnosed Problem = Paper Out - Printer",
                    "2. Call the store and ask the POC: 'The printer on Lane (#) is showing Out of Paper. Can you please put in a new roll of paper?'",
                    "3. If the paper is low or out, ask the POC: 'Can you please put in a new roll'",
                    "4. If the POC needs Help, provide instructions:",
                    "   - 'Put the paper in with letter side facing down'",
                    "   - 'Feed the paper roll through the top part of the paper door'",
                    "   - 'Close the door'",
                    "5. If No (store is out of paper):",
                    "   - Confirm with POC that the store is Out of Paper",
                    "   - Update the Equipment Line",
                    "   - Change Diagnosed Problem to Paper Out - Store",
                    "   - Equip Resolution Cat = Printer",
                    "   - Equip Resolution Method = Opened Ticket Level Incident",
                    "6. Recheck the Printer Status: Ready",
                    "7. Send a Test Print: Type 'Coup <Lane#>' and press enter",
                    "8. Check print quality",
                    "9. If Print Quality is good: Resolve issue",
                    "   - Equip Resolution Cat = Printer",
                    "   - Equip Resolution Method = Loaded Paper",
                    "   - Equip Status = Resolved - Remote (First, Second, Third) Call",
                    "10. If Print Quality is not good: Perform an ink cleaning (follow KBA3741)"
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
                kba="KBA4213",
                call_recording_needed=True,
                call_recording_id="CALL 2",
                detailed_steps=[
                    "1. Ensure Diagnosed Problem = Mechanical Error",
                    "2. Call the store:",
                    "   - Have the POC open the Paper Door",
                    "   - Remove the paper roll",
                    "   - Tilt the printer so they can see the top inside of the printer",
                    "   - Ask the POC: 'Do you see any paper in the front upper left or right side of the printer?'",
                    "3. For CMC6 ONLY:",
                    "   - MOVE THE PRINT HEAD (It may be silver)",
                    "   - Ask the POC to look on the inside top part of the paper compartment",
                    "   - If they see a small square metal plate, this will be the print head",
                    "   - POC should move the print head to the right and remove any debris that was causing it to be stuck",
                    "4. Important: Compressed air should NOT be used on a printer",
                    "5. Have the POC:",
                    "   - Put the paper roll back into the printer",
                    "   - Close the Paper Door",
                    "   - Reset the printer using the button located on the bottom left hand corner",
                    "   - Wait 30 seconds for the printer to initialize",
                    "   - NOTE: For CMC6 Printers Only",
                    "6. Recheck the Printer Status = Ready",
                    "7. Send a Test Print (Applies to Inbound calls only)",
                    "   - Type: 'Coup <Lane#>' and press enter",
                    "8. Check print quality",
                    "9. Is Print Quality good?",
                    "   - Yes: Resolve issue",
                    "     * Equip Resolution Cat = Printer",
                    "     * Equip Resolution Method = Cleared Paper Jam",
                    "     * Equip Status = Resolved - Remote (First, Second, Third) Call",
                    "   - No: Perform an ink cleaning (follow KBA4053)"
                ],
                special_notes=[
                    "FOR PRINTER OUTBOUND CALLS (SYSTEM ALERTS OR NON-POOR PRINT MAIL LISTEN TICKETS), AGENTS ARE NO LONGER REQUIRED TO SEND OR OFFER TO SEND TEST COUP(S) AFTER FIXING THE ISSUE",
                    "FOLLOW STANDARD POC UNWILLING PROCESS: KBA3880 L1C POC Unwilling to Assist",
                    "IF POC IS INSISTENT IN SENDING A TECH RIGHT AWAY: Agents need to escalate to a SME if a non-flagship store is demanding dispatch"
                ]
            ),
            PrinterIssue(
                system_alert_type="Ink Out / NR Error",
                caller_issue_type="Printer Making Sounds / Error light on printer / poor print quality / Blank Prints",
                resolution="Loaded Ink",
                impacted_equipment="CMC6",
                kba="KBA3812",
                call_recording_needed=True,
                call_recording_id="CALL 3",
                detailed_steps=[
                    "1. Ensure Diagnosed Problem = Out of Ink - Printer / No Cartridge (Ink)",
                    "2. Call the store: Ask the POC: 'The printer on Lane (#) is showing Out of Ink. Is there a new unopened ink cartridge available to put in the printer?'",
                    "3. If yes:",
                    "   - Ask the POC to remove the non-working cartridge and place it to the side",
                    "   - Open a new cartridge from the sealed package (This should be done while on the phone, even if they say this has already been done)",
                    "   - For CMC9 Ink cartridges: It is stored inside a brown box with a bright yellow Catalina label on both sides",
                    "   - Place the new cartridge in the printer and close the ink door",
                    "4. If the new cartridge doesn't work:",
                    "   - Remove the cartridge and place it to the side",
                    "   - Load an ink cartridge from a working printer",
                    "   - Then, place the new ink cartridge in the working printer and close the ink door",
                    "   - If the new ink still shows 'Out of Ink,' it indicates a faulty cartridge",
                    "   - If the printer still shows 'OUT OF INK' after using a second cartridge from a working printer, dispatch or replace the printer while on the phone",
                    "5. NOTE: CMC9 - Directs to follow 'Installing ink cartridge CMC9' (KBA3855)",
                    "6. NOTE: CMC7 - If the POC cannot get the ink cartridge out, directs to follow 'Ink Cartridge Not Ejecting' (KBA3785)",
                    "7. After ink is replaced:",
                    "   - The status light should flash, and the printer should perform an ink cleaning, which typically takes about 60 seconds",
                    "   - Once this is done, continue to Step 8",
                    "8. If No (store is out of ink):",
                    "   - Confirm with the POC t`hat the store is 'Out of Ink'",
                    "   - Update the Equipment Line",
                    "   - Change the Diagnosed Problem to 'Out of Ink - Store'",
                    "   - Set 'Equip Resolution Cat' to 'Printer'",
                    "   - Set 'Equip Resolution Method' to 'Opened Ticket Level Incident'",
                    "   - Set 'Equip Status' to 'Resolved - Remote (First, Second, Third) Call'",
                    "   - Follow 'Checking on Ink Deliveries' (KBA3815) to determine if ink is on the way or needs to be ordered",
                    "9. Recheck the Printer Status: Ready",
                    "10. Send a Test Print: Type 'Coup <Lane#>' and press enter",
                    "11. Check print quality",
                    "12. Is Print Quality good?",
                    "    - Yes: Resolve issue",
                    "      * Equip Resolution Cat = Printer",
                    "      * Equip Resolution Method = Loaded Ink",
                    "      * Equip Status = Resolved - Remote (First, Second, Third) Call",
                    "    - No: Perform an ink cleaning (follow KBA3741 for CMC6 or KBA4053)"
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
                kba="KBA4053",
                call_recording_needed=True,
                call_recording_id="CALL 4",
                detailed_steps=[
                    "1. Ensure Diagnosed Problem = Blank/Poor Print Quality",
                    "2. For Walgreens Mail Listen Tickets:",
                    "   - Perform an ink cleaning cycle on the printer BEFORE calling",
                    "   - Send an email using the 'Ink Cleaning Template'",
                    "   - Perform Complete Remote Ink Cleaning cycles",
                    "   - After completion, follow directions based on the Mail Listen template (Subject Line) used",
                    "3. For Remote Ink Cleaning:",
                    "   - We will be doing full ink cleaning remotely for the Catalina Printer at Register XXX",
                    "   - Step 1 (Ink Cartridge): If the printer starts beeping due to having no Ink Cartridge, replace it with a new cartridge coming from a sealed wrapper",
                    "   - Step 2 (Paper): If the printer starts beeping due to having no Paper, replace it with a new roll of Catalina Paper",
                    "   - Step 3 (Prints/Blank Paper during cleaning): If prints or blank paper come out during the cleanings this can be ignored, for the final test. Please view the one with the barcode",
                    "4. After ink cleaning:",
                    "   - Check print quality",
                    "   - If Print Quality is good: Resolve issue",
                    "     * Equip Resolution Cat = Printer",
                    "     * Equip Resolution Method = Ink Cleaning",
                    "     * Equip Status = Resolved - Remote (First, Second, Third) Call",
                    "5. If Print Quality is still not good:",
                    "   - For Walgreens and CMC9 Printers: Order a replacement printer - follow the Ordering Process (KBA3739)",
                    "   - For CMC8: Follow SITA Printer Repair Process (KBA3738)",
                    "   - All others: Follow the Equipment Level Dispatching Process (KBA3746)",
                    "6. For Flagship stores:",
                    "   - If remote ink cleaning successfully resolves a blank coupon or poor print issue, the agent must inform the POC: 'To be proactive, we are going to dispatch a tech to replace the printer.'",
                    "   - When dispatching, include in tech special instructions: 'habitual problem, tech MUST replace printer.'",
                    "   - Indicate on Incident/Request Description Field: 'Printer on tid X is a habitual problem and must be replaced'"
                ],
                special_notes=[
                    "CMC6 Ink Cleaning (KBA3741)",
                    "For Kroger Chains: Blank coupon - Dispatch to replace the Printer if the issue happens again for the same printer",
                    "For Kroger Chains: Poor Print - Do not dispatch if the issue is resolved remotely"
                ]
            ),
            PrinterIssue(
                system_alert_type="PC No Comm",
                caller_issue_type="Store not printing / Promos not printing",
                resolution="PC Reboot",
                impacted_equipment="CMC6",
                kba="KBA4057",
                call_recording_needed=True,
                call_recording_id="CALL 5",
                detailed_steps=[
                    "1. Ensure Diagnosed Problem = PC No Comm / No Vault Heartbeats",
                    "2. Try to connect to the store (Follow KBA4047 Logging to a store)",
                    "3. Is the store commable through PuTTY?",
                    "   - Yes: Go to KBA4056 No Vault Heartbeats. To verify that the Vitals are good",
                    "   - No: Continue",
                    "4. Call the store:",
                    "   - State: 'We are not able to connect to the store. I need some help checking on the Catalina PC.'",
                    "   - Use the storemaster list to determine the make and model of the PC",
                    "   - Appearance: It will look like a home desktop computer (tower)",
                    "   - Sticker: It should have a blue & white sticker on it that states 'Property of Catalina Marketing.'",
                    "   - Peripherals: There is usually a monitor and keyboard attached",
                    "   - Monitor: Most stores use a 9-inch TVS brand monitor or share a monitor with another PC",
                    "   - Brand Names: Some of the brand names Catalina uses that the POC might see on the tower include: Fujitsu, IBM, HP",
                    "5. Locate the PC:",
                    "   - Log into: https://storemaster.catalinamarketing.com/ using network username and password",
                    "   - Click on the Store Information Tab",
                    "   - Select chain number from the drop-down in the Search Option, then select the chain number in the value drop-down box and press the + symbol",
                    "   - Select Store number from the drop-down in the Search Option, then select the store number in the value drop-down box, press the + symbol, and then select search",
                    "   - Go to the PC Manufacture and PC Model",
                    "   - If POC unable to find PC: Follow 'Locating a Store PC (KBA3173)'",
                    "6. Have the POC turn on/reboot the PC:",
                    "   - Ask: 'Does the PC have Power?' 'Do you see a green light on the Tower?' 'What do you see on the monitor?'",
                    "   - Instructions to POC for Reboot: 'I need you to reboot the PC. Please press and hold the power button on the tower until the PC turns off. Let me know once it Powers off.'",
                    "   - After shutdown wait 45 to 60 seconds: 'Please press the power button again and let me know once the PC is back on'",
                    "   - Ask: 'Did the PC Power on?'",
                    "7. If PC still No Comm:",
                    "   - No - Did the PC Originally have Power?",
                    "   - If PC still does not have power:",
                    "     * Have the POC check the PC power connections",
                    "     * Is the power cord plugged into an outlet?",
                    "     * Is the power cord connected to the Tower?",
                    "     * Does the outlet have power?",
                    "   - If the PC regains power, Continue to Step 8: Try connecting to the store",
                    "   - If the PC still does not have power:",
                    "     * Change Diagnosed Problem to PC Won't Power On",
                    "     * Go to Agent special instructions KBA4083 prior to step 9 dispatching",
                    "   - If the POC unable to access/trace the power:",
                    "     * Change Diagnosed Problem = PC Won't Power On",
                    "     * In Tech Special Instructions add/paste 'POC unable to locate PC power supply'",
                    "     * Go to Agent special instructions KBA4083 prior to step 9 dispatching",
                    "8. Try connecting to the store again (follow KBA4047 Logging to a store) - Is the PC Commable?",
                    "   - Yes: Continue",
                    "   - No: If after 2-3 minutes, the store is still not commable via SSH (Putty), agent will have to dispatch a tech to reload the software",
                    "9. If PC gives boot options: select Linux, if it doesn't give boot options, continue to next step",
                    "10. If PC reboots to Emergency Mode screen: without the option to boot into Windows, agent will have to dispatch a tech to reload the software",
                    "11. Check for commability: See KBA4047 L1C Store 3.0 Logging into a store",
                    "12. If PC gives boot options and fails to load Linux properly:",
                    "    - Reboot the PC again, have the POC select Windows",
                    "    - If the PC boots into Windows normally escalate ticket to Implementation immediately",
                    "    - If Windows does not boot successfully, agent will have to dispatch a tech to reload the software",
                    "13. Check store vitals (KBA4056):",
                    "    - Was store vitals good?",
                    "    - Yes: Resolve Issue",
                    "      * Equip Resolution Cat = Printer",
                    "      * Equip Resolution Method = PC Reboot",
                    "      * Equip Status = Resolved - Remote (First, Second, Third) Call",
                    "    - No: Power Cycled PC",
                    "14. If dispatch is needed:",
                    "    - Add #Delayed_Dispatch No Comm in the top of the Incident/Request Description field",
                    "    - Add #Rebooted_PC on the Resolution Field, this should only be added if the POC was able to reboot the PC",
                    "    - Follow the Equipment Level Dispatching Process (KBA3746)"
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
                kba="KBA4078",
                call_recording_needed=True,
                call_recording_id="CALL 6",
                detailed_steps=[
                    "1. Ensure Diagnosed Problem = Printer No Response",
                    "2. For all 'No Response' tickets, the POC must confirm that the Ethernet, Status, and USB printer server lights are all green",
                    "3. The 'wireless' light is not used and will always be blank",
                    "4. Ask the POC which LEDs are lit on the front Panel of the Printer. Be sure to ask if it's solid or blinking since they have different troubleshooting steps",
                    "5. If solid green: refer to the NO RESPONSE PRINTER - SOLID GREEN LIGHT section",
                    "6. If blinking: refer to the NO RESPONSE PRINTER - FLASHING GREEN LIGHT section",
                    "7. If it's off: NO RESPONSE PRINTER - GREEN POWER LIGHT NOT LIT (NO POWER) section",
                    "8. NO RESPONSE PRINTER - SOLID GREEN LIGHT:",
                    "   - Step 1: Have POC remove the back cover of the printer",
                    "   - Step 2: Ask POC to read to you the color of each light on the left side of the printer server (except for the wireless, which will always be blank)",
                    "   - DO NOT ask 'Are all of the lights green?'",
                    "   - If any lights are red, refer to the section that deals with that particular light",
                    "   - Step 3: If all lights are green on the printer server, proceed to STEPS TO CYCLING THE PRINTER POWER",
                    "9. NO RESPONSE PRINTER - FLASHING GREEN LIGHT:",
                    "   - Step 1: Press and hold the square reset button until the paper advances",
                    "   - Step 2: Ping the printer (call ping 192.168.192.lane number) then press <enter>",
                    "   - Step 3: If pinging the printer returns a request a time out, have POC remove the back cover of the printer and inform you of the color of ALL lights on the printer server",
                    "10. NO RESPONSE PRINTER - GREEN POWER LIGHT NOT LIT (NO POWER):",
                    "   - Step 1: Ask the POC is the lane has power. Have them power it on if it doesn't",
                    "   - Step 2: If printer regains power and comes ready, send a test coupon to confirm print quality",
                    "   - Step 3: If still no power to printer, have POC remove the back cover, confirm if the power cable on the right bottom most corner is plugged in",
                    "   - Disconnect and reconnect the three wires/cables in the lower right-hand corner of the back of the printer",
                    "   - Step 4: If printer regains power and comes ready then close the ticket and if issue persist proceed on the next step",
                    "   - For Walgreens only - If power cable is not plugged in follow #2 of Walgreens/Duane Reade Process",
                    "11. STEPS TO CYCLING THE PRINTER POWER:",
                    "   - Step 1: Have the POC remove the back cover of the printer",
                    "   - Step 2: The power cord is located on the bottom right hand corner of the printer",
                    "   - Step 3: It may be easier for the POC to access the power cord if the POC disconnects the two wires (USB and Printer Server wires) above the power cord",
                    "   - Step 4: The power cord has a coupler or spring sleeve that will need to be pulled back for disconnection. Leave power cord disconnected for 30 seconds",
                    "   - Step 5: If disconnected in step 3, re-connect the other two wires (USB and printer server wires) that are above the power cord",
                    "   - Step 6: Reseat the two wires connected to the printer server box (Ethernet and other end of the printer server wire)",
                    "   - The printer server is the square 'box' to the left of the USB/printer server/power cord wires",
                    "   - Step 7: Reconnect the power cord: identify the flat side of the wire with the arrow on it. This side goes towards the outside of the printer",
                    "   - The POC may have to wiggle the wire so the prongs line up",
                    "   - Step 8: Ask POC to read to you the color of each light on the left side of the printer server",
                    "   - DO NOT ask 'Are all of the lights green?'",
                    "   - If all the lights are green, does the printer show ready?",
                    "   - Yes - send a test coupon to ensure the printer is producing quality prints and close ticket as reset printer",
                    "   - No - go to section STEPS TO CYCLING THE PRINTER POWER. If printer is still no response after following ALL steps, dispatch ticket",
                    "12. TROUBLESHOOTING A RED STATUS LIGHT:",
                    "   - Instruct the POC to reconnect the Ethernet cable, which is located on the right side of the printer server",
                    "   - If already connected: Have the POC disconnect and reconnect (reseat) the cable, gently tugging to ensure it's locked",
                    "   - The light should turn orange for approximately 30 seconds, then turn green",
                    "   - If light turns green: Check printer status (F3) and send a test coupon",
                    "   - If light does not turn green: Proceed to STEPS TO CYCLING THE PRINTER POWER section",
                    "13. TROUBLESHOOTING A RED USB LIGHT:",
                    "   - Instruct the POC to reconnect the USB cable",
                    "   - If already connected: Have the POC disconnect and reconnect (reseat) the cable",
                    "   - The light should turn orange for approximately 30 seconds, then turn green",
                    "   - If light turns green: Check printer status (F3) and send a test coupon",
                    "   - If light does not turn green: Proceed to STEPS TO CYCLING THE PRINTER POWER section",
                    "14. After power cycle and the LEDs finally lit up yet the printer is still offline:",
                    "   - Exit out of the catalina directory and enter 'sudo systemctl restart epurasd'",
                    "   - If the printer is still No Response please send ticket to Delayed Dispatch Bot/ Queue",
                    "15. For Walgreens: There is no need to swap with a working printer, immediately order a printer for the lane",
                    "16. Printer is in an Error state (example Paper Jam):",
                    "   - Have the POC open the Paper Door",
                    "   - Remove the paper roll",
                    "   - Tilt the printer so they can see the top inside of the printer",
                    "   - Ask the POC 'Do you see any paper in the front upper left or right side of the printer?'",
                    "   - MOVE THE PRINT HEAD (It may be silver): Ask the POC to look on the inside top part of the paper compartment",
                    "   - If they see a small square metal plate, this will be the print head",
                    "   - POC should move the print head to the right and remove any debris that was causing it to be stuck",
                    "   - Compressed air should not be used on a printer",
                    "   - Have the POC put the paper roll back into the printer",
                    "   - Close the Paper Door",
                    "   - Reset the printer using the button located on the bottom left hand corner (NOTE: Pressing the reset button is not needed for CMC9 Printer)",
                    "   - Wait 30 seconds for the printer to initialize",
                    "   - Recheck the Printer Status = Idle",
                    "   - Send a Test Print"
                ],
                special_notes=[
                    "For all 'No Response' tickets, the POC must always be instructed to remove the back cover of the printer and confirm that all five wires are fully plugged into the ports on the back of the printer",
                    "For HEB Stores (Chain 214): Refer to special handling note in KBA 3717",
                    "Agent must log into Putty (referencing KBA4047) and verify the printer status",
                    "If printer status shows 'Error,' refer to Section 5 of this KBA"
                ]
            ),
            PrinterIssue(
                system_alert_type="Printer Shows Offline (But Firmware Good)",
                caller_issue_type="Printer Not Printing",
                resolution="Printer SW - Not Commable (Restart Services)",
                impacted_equipment="CMC6",
                kba="KBA4078",
                call_recording_needed=True,
                call_recording_id="CALL 7",
                detailed_steps=[
                    "1. Ensure Diagnosed Problem = Printer No Response / Offline",
                    "2. Log into Putty (referencing KBA4047) and verify the printer status",
                    "3. Does the printer still show the issue in Putty?",
                    "   - Yes: continue with the dispatch",
                    "   - No: Proceed to ticket closure instructions",
                    "4. If No issue in Putty:",
                    "   - Close the ticket using the appropriate codes",
                    "   - Send an email to the Customer Service Desk team at callcenterescalation@catalina.com",
                    "   - Email must include the chain and store, lane number(s), and ticket number",
                    "   - State that 'the Store Master List did not update'",
                    "5. Printer Statuses:",
                    "   - Idle: The printer is ready",
                    "   - Busy: The printer is either printing or performing an ink cleaning cycle",
                    "   - Off Line: This status indicates that the power or ethernet cable is most likely unplugged from the printer",
                    "   - Error: This status most likely signifies a paper jam or a mechanical error",
                    "6. To send a test print:",
                    "   - For CMC6 printer: Have the POC remove the back cover and using something small press the black button for 2 seconds (no longer or else a very long print will print) located on the back of the printer",
                    "   - Type: 'Coup <Lane#>' and press enter",
                    "7. If printer is still offline after troubleshooting:",
                    "   - Follow Agents special instructions in KBA and only continue to next steps if advised",
                    "   - For Walgreens and CMC9 Printers: Order a replacement printer - follow the Ordering Process (KBA3739)",
                    "   - For CMC8: Follow SITA Printer Repair Process (KBA3738)",
                    "   - All others: Follow the Equipment Level Dispatching Process (KBA3746)"
                ],
                special_notes=[
                    "DO NOT TOUCH/Rework Tickets: Agents are instructed not to touch or rework tickets that have specific notes in the Resolution field",
                    "When a ticket is due for closure, dispatch, or escalation, any notes related to these actions should be removed from the Resolution field if they are no longer applicable",
                    "See KBA4083 Store 3.0 Agents Special Instructions for further guidance"
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
    
    def get_by_kba(self, kba: str) -> Optional[PrinterIssue]:
        """Get printer issue by KBA number"""
        for issue in self.issues:
            if issue.kba.upper() == kba.upper():
                return issue
        return None
    
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
                "1. Open the paper tray",
                "2. Check if paper is properly loaded",
                "3. Ensure paper is aligned correctly",
                "4. Close the paper tray",
                "5. Test print to verify resolution"
            ],
            "Cleared Paper Jam": [
                "1. Turn off the printer",
                "2. Open all access panels",
                "3. Gently remove any jammed paper",
                "4. Check for any torn paper pieces",
                "5. Close all panels",
                "6. Turn printer back on",
                "7. Test print to verify resolution"
            ],
            "Loaded Ink": [
                "1. Open the ink cartridge access door",
                "2. Remove the empty or low ink cartridge",
                "3. Install the new ink cartridge",
                "4. Ensure cartridge is properly seated",
                "5. Close the access door",
                "6. Run printer cleaning cycle if needed",
                "7. Test print to verify resolution"
            ],
            "Ink Cleaning": [
                "1. Access printer maintenance menu",
                "2. Select 'Ink Cleaning' or 'Print Head Cleaning'",
                "3. Follow on-screen prompts",
                "4. Wait for cleaning cycle to complete",
                "5. Test print to verify resolution"
            ],
            "PC Reboot": [
                "1. Save any open work",
                "2. Close all applications",
                "3. Restart the PC",
                "4. Wait for PC to fully boot",
                "5. Check printer connection",
                "6. Test print to verify resolution"
            ],
            "Plugged-in Printer Power Cord": [
                "1. Check if power cord is properly connected to printer",
                "2. Check if power cord is connected to power outlet",
                "3. Verify power outlet is working",
                "4. Ensure power switch is in ON position",
                "5. Check for any visible damage to power cord",
                "6. Test printer power on"
            ],
            "Printer SW - Not Commable (Restart Services)": [
                "1. Access the printer software/service panel",
                "2. Stop the printer service",
                "3. Wait 10 seconds",
                "4. Start the printer service",
                "5. Verify service is running",
                "6. Check printer connection status",
                "7. Test print to verify resolution"
            ]
        }
        
        return resolution_steps.get(issue.resolution, [
            f"Follow the resolution steps for: {issue.resolution}",
            f"Refer to {issue.kba} for detailed instructions"
        ])
