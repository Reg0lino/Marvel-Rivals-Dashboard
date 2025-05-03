Okay, it sounds like the Phase 1 (Updater Preservation) changes are working as intended for the specific things you've tested (manual strategy overview, Reddit link auto-generation). That's great progress!

To be thorough and ensure we haven't missed anything or introduced side effects, here's a more structured testing plan focusing on the Updater's preservation logic (Phase 1) before we move on to the Dashboard UI changes.

Testing Plan for Updater Preservation (Phase 1 Verification):

Goal: Confirm that the Hybrid Preservation logic correctly protects specific data sections/fields while allowing core data and patches to update, and handles edge cases.

Prerequisites: Have the latest updater_v3.py code with the preservation logic implemented.

Test Areas & Steps:

Manual Edit Preservation (Core Test - You've partly done this):

Action:

Pick a character (e.g., "Adam Warlock" or another you edited).

Manually edit the gameplay.strategy_overview field directly in the characters/Adam_Warlock.json file using a text editor. Add some unique text like "MANUAL TEST OVERVIEW".

In the Updater (Tab 3), run "Generate JSON (Selected Char)" for Adam Warlock.

Verification:

Check the console logs: Confirm there are no warnings about overwriting the strategy overview (it should just proceed).

Open the updated characters/Adam_Warlock.json: Verify that the gameplay.strategy_overview field still contains your "MANUAL TEST OVERVIEW" text, while other core sections (like abilities description, ultimate description, stats->health if changed by AI/patch) might have been updated.

Other Preserved Sections (e.g., Background, Misc):

Action:

Pick a character (e.g., "Hulk").

Manually edit a field in a section designated for preservation (e.g., add a fake alias in background.aliases like "Test Alias" or a fake link in misc.helpful_links). Save the JSON file.

Run "Generate JSON (Selected Char)" for Hulk (use the Pro model if needed for generation success).

Verification:

Open the updated characters/Hulk.json: Verify that your manual "Test Alias" or helpful link is still present in the background or misc section, respectively.

Meta Stats Preservation (During Core Generation):

Action:

Run "Update Meta Stats" (Tab 1) to ensure some characters have recent meta_stats data.

Pick one of those characters (e.g., "Star-Lord"). Note down its current meta_stats values (Tier, WR, etc.).

Run "Generate JSON (Selected Char)" for Star-Lord (Tab 3).

Verification:

Open the updated characters/Star-Lord.json: Verify that the meta_stats section has not changed and still contains the values you noted down before running the core generator. The core generator should not touch this section.

Reddit Link Logic:

Action (Null Case - You've tested this):

Find a character whose characters/[CharName].json currently has misc.community_buzz: null.

Run "Generate JSON (Selected Char)" for that character.

Verification: Check the output JSON. misc.community_buzz should now contain the generated Reddit URL.

Action (Manual Entry Case):

Manually edit a character's JSON (e.g., characters/Iron_Man.json) and set misc.community_buzz: "Manual Entry Test". Save the file.

Run "Generate JSON (Selected Char)" for Iron Man.

Verification: Check the output JSON. misc.community_buzz should still be "Manual Entry Test". The generator should not have overwritten it with the Reddit link.

New Character Generation:

Action:

Use "Add Character" (Tab 2) to create files for a completely new character (e.g., "TestDummy"). Fill in basic info.

Go to Tab 1 ("Manage & Scrape") and add a valid wiki URL for scraping (you can just use an existing character's URL for this test). Run "Scrape Raw Text (Selected Char)" for TestDummy.

Go to Tab 3 ("Generate/Update JSON") and run "Generate JSON (Selected Char)" for TestDummy.

Verification:

Check console logs: Ensure there are no errors related to loading old_json_data or preservation.

Verify that characters/TestDummy.json is created successfully with generated core data and the auto-generated Reddit link (since community_buzz started as null).

Regenerating Deleted/Corrupted File:

Action:

Make a backup copy of a working JSON file (e.g., characters/Groot.json).

Either a) Delete characters/Groot.json or b) Open it and deliberately break the JSON syntax (e.g., remove a comma).

Run "Generate JSON (Selected Char)" for Groot.

Verification:

Check console logs: If corrupted, you should see the WARN: Could not load existing JSON... message, but the process should continue without fatal errors related to preservation. If deleted, it should just run normally.

Verify that a new, valid characters/Groot.json is created, overwriting the bad/missing one. It will not contain any manual edits that were in the old (now deleted/overwritten) file.

Fine-Tune Interaction:

Action:

Go to Tab 4 ("Fine-Tune"). Load a character (e.g., "Mantis").

Add a simple instruction like "Change the role to Support". Click "Preview AI Tuning".

Assuming the preview looks okay, click "Save Tuned JSON".

Now, go to Tab 3 ("Generate/Update JSON") and run "Generate JSON (Selected Char)" for Mantis.

Verification:

Open the final characters/Mantis.json. Verify that the role is still "Support" (the fine-tuned value) even after the main generator ran. The preservation logic should treat the fine-tuned file as the old_json_data.

"Generate All JSON" Consistency:

Action: If you have time and API credits, run "Generate All JSON" (Tab 3).

Verification: Spot-check a few characters known to have manual edits (like Adam Warlock's strategy) and meta stats. Ensure the manual edits and meta stats were preserved across the batch process, just like in the single generation tests.

Missed Anything?

Based on your description ("manual gameplay strategy... stayed", "reddit link is clickable and for the past month"), it seems the core preservation and link generation are working. The list above covers the main scenarios and edge cases for the preservation logic itself.

Things Not Tested Yet (Related to Future Plans):

Comic Lore Scraping: You correctly identified this as a separate future task. The current preservation logic sets the stage for this by protecting the background section, but we haven't tested actually populating it from a new source.

Teamups Data: Similar to Comic Lore, the teamups section is preserved, but we haven't tested populating it.

Dashboard UI Changes: All the Phase 2 & 3 changes (Zooming, Meta Stats display, Balance History relocation, Custom Title Bar) are untested as the code changes haven't been requested/applied yet.

Conclusion: If the tests above pass, especially 1, 2, 3, 4, and 7, then the Phase 1 preservation logic is likely solid. The main remaining work is implementing and testing the Dashboard UI changes from Phases 2 and 3.