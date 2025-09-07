import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

import discord
import pytz
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


@dataclass(frozen=True)
class ChannelSubscription:
    channel_id: int
    timezone: pytz.BaseTzInfo


def local_time_str(dt: datetime, timezone: pytz.BaseTzInfo) -> str:
    """Format datetime with timezone."""
    return dt.astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")


def check_end_time(end_time: datetime) -> int:
    """Check if the end time is exact 7days, 3days, or 1 day away. Only return 7, 3, or 1 if it matches exactly. Return -1 if not."""
    now = datetime.now(pytz.utc)
    print(f"Current time: {now}")
    print(f"End time: {end_time}")
    delta_hour = int((end_time - now).total_seconds()) // 3600
    print(delta_hour)

    if delta_hour == 24 * 7:
        return 7
    elif delta_hour == 24 * 3:
        return 3
    elif delta_hour == 24:
        return 1

    return -1


def main():
    args = parser.parse_args()

    print("Fetching pre-order items...")
    fms = FindMeStoreItemList()
    items = fms.get_items(fill_preorder_period=True)

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
            subscribe_channel_ids: list[ChannelSubscription] = []
            for channel_id_row in file.read().strip().splitlines():
                channel_id, tz = channel_id_row.split(",")
                subscribe_channel_ids.append(
                    ChannelSubscription(
                        int(channel_id.strip()), pytz.timezone(tz.strip())
                    )
                )
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

        items_by_end_time: Mapping[datetime, list[ItemDetails]] = {}
        nonlocal items
        for item in items:
            if not item.preorder_period:
                continue
            end_time = item.preorder_period.end_time
            if end_time not in items_by_end_time:
                items_by_end_time[end_time] = []
            items_by_end_time[end_time].append(item)

        await client.wait_until_ready()
        for channel_sub in subscribe_channel_ids:
            channel = client.get_channel(channel_sub.channel_id)
            if channel:
                for end_time, items in items_by_end_time.items():
                    end_time_check = check_end_time(end_time)
                    if end_time_check == -1:
                        continue
                    if not items:
                        continue
                    end_time_str = local_time_str(end_time, channel_sub.timezone)
                    embeds = []
                    # Create an embed for every 10 items
                    for i in range(0, len(items), 10):
                        item_slice = items[i : i + 10]
                        item_list = "\n".join(
                            f"[{item.title}]({item.link})" for item in item_slice
                        )
                        embed = discord.Embed(
                            description=f"Items ending at {end_time_str}\n{item_list}",
                            color=discord.Color.blue(),
                        )
                        embeds.append(embed)
                    title = f"### 🚨🚨🚨 以下 {len(items)} 件商品將在 {end_time_check} 天後截止 🚨🚨🚨"
                    await channel.send(content=title, embeds=embeds)  # type: ignore
            else:
                print(f"Channel with ID {channel_id} not found.")

        await client.close()

    client.run(token)


if __name__ == "__main__":
    main()
