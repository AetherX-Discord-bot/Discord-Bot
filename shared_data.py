from datetime import datetime, timezone

class SnipeData:
    last_deleted = {} 
    
    @classmethod
    def record_deleted_message(cls, message):
        if not message.author.bot:
            cls.last_deleted[message.channel.id] = {
                "content": message.content,
                "author": message.author,
                "timestamp": message.created_at,
                "message_id": message.id,
                "attachments": message.attachments,
                "deleted_at": datetime.now(timezone.utc)
            }