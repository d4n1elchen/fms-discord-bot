import argparse
from datetime import datetime
from typing import Mapping

import discord
from fmslist import FindMeStoreItemList, ItemDetails

parser = argparse.ArgumentParser(
    description="Discord Bot for FindMeStore Preorder Notifications"
)
parser.add_argument(
    "--token_file",
    type=str,
    help="The path to the file containing the Discord bot token.",
    default="token.txt",
)
parser.add_argument(
    "--channel_id_file",
    type=str,
    help="The path to the file containing the channel IDs to subscribe to. Separate multiple IDs with line breaks.",
    default="channels.txt",
)


def main():
    args = parser.parse_args()

    try:
        with open(args.token_file, "r") as file:
            token = file.read().strip()
    except FileNotFoundError:
        print(f"Token file '{args.token_file}' not found.")
        return

    if not token:
        print("Token file is empty.")
        return

    try:
        with open(args.channel_id_file, "r") as file:
            subscribe_channel_ids = [
                int(channel_id)
                for channel_id in file.read().strip().splitlines()
                if channel_id.isdigit()
            ]
    except FileNotFoundError:
        print(f"Channel ID file '{args.channel_id_file}' not found.")
        return

    if not subscribe_channel_ids:
        print("No valid channel IDs found in the channel ID file.")
        return

    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")

        print("Fetching pre-order items...")
        fms = FindMeStoreItemList()
        items = fms.get_items(fill_preorder_period=True)

        items_by_end_time: Mapping[datetime, list[ItemDetails]] = {}
        for item in items:
            if not item.preorder_period:
                continue
            end_time = item.preorder_period.end_time
            if end_time not in items_by_end_time:
                items_by_end_time[end_time] = []
            items_by_end_time[end_time].append(item)

        await client.wait_until_ready()
        for channel_id in subscribe_channel_ids:
            channel = client.get_channel(channel_id)
            if channel:
                for end_time, items in items_by_end_time.items():
                    if not items:
                        continue
                    embeds = []
                    # Create an embed for every 10 items
                    for i in range(0, len(items), 10):
                        item_slice = items[i : i + 10]
                        item_list = "\n".join(
                            f"[{item.title}]({item.link})" for item in item_slice
                        )
                        embed = discord.Embed(
                            description=f"Items ending at {end_time}\n{item_list}",
                            color=discord.Color.blue(),
                        )
                        embeds.append(embed)
                    title = f"There are {len(items)} items ending at {end_time}"
                    await channel.send(content=title, embeds=embeds)  # type: ignore
            else:
                print(f"Channel with ID {channel_id} not found.")

        await client.close()

    client.run(token)


if __name__ == "__main__":
    main()
