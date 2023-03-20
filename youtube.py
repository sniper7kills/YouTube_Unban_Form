import os
import base64
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

class youtube:
    api = None
    channel_id = None
    stream_id = None
    live_chat_id = None

    def __init__(self, config_file) -> None:
        scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = config_file

        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()
        self.api = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)
        
        self.get_initial_values()


    def get_initial_values(self):
        broadcast_list = self.getBroadcastList()

        self.channel_id = broadcast_list["items"][0]["snippet"]["channelId"]
        self.live_chat_id = broadcast_list["items"][0]["snippet"]["liveChatId"]
        self.stream_id = broadcast_list["items"][0]["id"]

    def getBroadcastList(self):
        request = self.api.liveBroadcasts().list(
            part="snippet,contentDetails,status",
            broadcastStatus="active",
            broadcastType="all"
        )
        return request.execute()
    
    def unban(self, channel_id):
        # Generate Unban ID
        decoded = f"\x08\x01\x12\x18{channel_id}\x1a)*'\n\x18{self.channel_id}\x12\x0b{self.stream_id}".encode('utf-8')
        encoded = base64.b64encode(decoded).decode('utf-8')

        request = self.api.liveChatBans().delete(
            id=encoded
        )
        request.execute()

    def ban(self, channel_id):
        request = self.api.liveChatBans().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": self.live_chat_id,
                    "type": "permanent",
                    "bannedUserDetails": {
                        "channelId": channel_id
                    }
                }
            }
        )
        response = request.execute()