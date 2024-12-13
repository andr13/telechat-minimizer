import json
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def minimize_telegram_json(input_file, output_file, no_media=False, no_reactions=False):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading JSON file: {e}")
        return

    messages = data.get('messages', [])
    if not messages:
        logging.error("No messages found in the JSON data.")
        return

    # Fixed alias mapping table using 'from' values
    alias_table = {}
    unique_names = []
    for msg in messages:
       if msg.get('from') not in unique_names:
            unique_names.append(msg.get('from'))

    if len(unique_names) == 2:
      alias_table = {unique_names[0] : "A", unique_names[1] : "B"}
    else:
      alias_table = {k: chr(65 + i) for i,k in enumerate(unique_names)}
    
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Output alias table and a description for LLMs
            outfile.write(f'# Alias Table: {alias_table}. This table maps sender names to single-character aliases.\n')

            # Generate dynamic header based on flags
            header = "# Each message is represented in the following format: [msg_index,from,reply_to,date,text"
            if not no_reactions:
                header += ",[reaction_emoji,reactor_alias],[reaction_emoji,reactor_alias]..."
            header += "]. 'msg_index' is the message index (starting at 1), 'from' is the sender's alias, 'reply_to' is the message index this message replies to (if any, otherwise empty), 'date' is the message sent time, 'text' is the message text"
            if not no_reactions:
                header += ", and subsequent elements are reactions (emoji symbol, reactor alias)."
            outfile.write(header + "\n\n")

            minified_messages = []

            for index, msg in enumerate(messages):
              try:
                # Check if the message is a pure media message if no_media is set
                if no_media and not msg.get('text') and (msg.get('photo') or (msg.get('file') and msg.get('media_type') == "sticker")):
                  continue
                
                minified_msg = [len(minified_messages)+1]

                from_name = msg.get('from')
                minified_msg.append(alias_table.get(from_name, ''))

                if 'reply_to_message_id' in msg:
                    original_reply_id = msg['reply_to_message_id']
                    reply_index = next((i+1 for i, m in enumerate(messages) if m.get('id') == original_reply_id and not (no_media and not m.get('text') and (m.get('photo') or (m.get('file') and m.get('media_type') == "sticker"))) ), None)
                    if reply_index:
                        minified_msg.append(reply_index)
                    else:
                        minified_msg.append('')
                else:
                   minified_msg.append('')

                minified_msg.append(msg.get('date', ''))
                text = msg.get('text', '')
                if not text and not no_media:
                   if msg.get('photo'):
                        text = '[photo]'
                   elif msg.get('file') and msg.get('media_type') == "sticker":
                        text = '[sticker]'
                minified_msg.append(text)

                if not no_reactions:
                  reactions = msg.get('reactions', [])
                  if reactions:
                      for reaction in reactions:
                            reactors = reaction.get('recent',[])
                            for reactor in reactors:
                                if reactor.get('from') in alias_table:
                                  minified_msg.append([
                                      reaction.get('emoji', ''),
                                      alias_table.get(reactor.get('from'))
                                  ])
                
                minified_messages.append(minified_msg)
                outfile.write(str(minified_msg) + "\n")
              except Exception as e:
                  logging.error(f"Error processing message {msg.get('id')}: {e}")
    except Exception as e:
        logging.error(f"Error writing to output file: {e}")
        return

    print(f"Minification complete! Minified data written to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Compresses Telegram personal chat export JSON to minimize token consumption by LLMs.
This script simplifies exported Telegram JSON files by removing non-essential elements, reducing file size and optimizing the content for use with AI tools.""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="path to the input JSON file")
    parser.add_argument("output_file", help="path to the output text file")
    parser.add_argument("--no-media", action="store_true", help="remove all media-only messages from output")
    parser.add_argument("--no-reactions", action="store_true", help="remove reaction data from the output")
    parser.add_argument("-a", "--aggressive", action="store_true", help="equivalent to --no-media and --no-reactions together")
    
    args = parser.parse_args()

    no_media = args.no_media or args.aggressive
    no_reactions = args.no_reactions or args.aggressive


    minimize_telegram_json(args.input_file, args.output_file, no_media, no_reactions)