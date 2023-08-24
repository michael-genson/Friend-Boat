# Friend Boat

A simple music bot for Discord. Open source so you can host it yourself in your quest to minimize downtime.

## Usage/Deployment
[Deploy with docker](https://hub.docker.com/r/mgenson/friend-boat) and set the following environment variables:
- DISCORD_BOT_TOKEN="[your-discord-bot-token](https://discord.com/developers/applications)"
- YOUTUBE_API_KEY="[your-youtube-data-api-key](https://developers.google.com/youtube/v3)"


## Development
Clone the repo (preferably using [VSCode Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)), create an "env" directory in the root of the repo, then add a "secrets.sh" file with your test token and api key:
```shell
export DISCORD_BOT_TOKEN="your-test-discord-bot-token"
export YOUTUBE_API_KEY="your-youtube-data-api-key"
```
