# data/models.py
from datetime import datetime


class PlexUser:
    """Modèle représentant un utilisateur Plex"""

    def __init__(
        self,
        user_id,
        username,
        email=None,
        phone=None,
        is_whitelisted=False,
        max_streams=1,
        notes=None,
    ):
        self.id = user_id
        self.username = username
        self.email = email
        self.phone = phone
        self.is_whitelisted = is_whitelisted
        self.max_streams = max_streams
        self.notes = notes
        self.last_seen = datetime.now()

    def to_dict(self):
        """Convertir l'objet en dictionnaire"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "is_whitelisted": 1 if self.is_whitelisted else 0,
            "max_streams": self.max_streams,
            "notes": self.notes,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }

    @classmethod
    def from_dict(cls, data):
        """Créer une instance à partir d'un dictionnaire"""
        user = cls(
            user_id=data.get("id"),
            username=data.get("username"),
            email=data.get("email"),
            phone=data.get("phone"),
            is_whitelisted=bool(data.get("is_whitelisted", 0)),
            max_streams=data.get("max_streams", 1),
            notes=data.get("notes"),
        )

        last_seen = data.get("last_seen")
        if last_seen:
            try:
                user.last_seen = datetime.fromisoformat(last_seen)
            except (ValueError, TypeError):
                user.last_seen = datetime.now()

        return user


class PlexSession:
    """Modèle représentant une session Plex"""

    def __init__(
        self,
        session_id,
        user_id,
        platform=None,
        device=None,
        ip_address=None,
        media_title=None,
        library_section=None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.platform = platform
        self.device = device
        self.ip_address = ip_address
        self.media_title = media_title
        self.library_section = library_section
        self.start_time = datetime.now()
        self.end_time = None
        self.was_terminated = False

    def terminate(self):
        """Marquer la session comme terminée"""
        self.end_time = datetime.now()
        self.was_terminated = True

    def to_dict(self):
        """Convertir l'objet en dictionnaire"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "platform": self.platform,
            "device": self.device,
            "ip_address": self.ip_address,
            "media_title": self.media_title,
            "library_section": self.library_section,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "was_terminated": 1 if self.was_terminated else 0,
        }

    @classmethod
    def from_dict(cls, data):
        """Créer une instance à partir d'un dictionnaire"""
        session = cls(
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            platform=data.get("platform"),
            device=data.get("device"),
            ip_address=data.get("ip_address"),
            media_title=data.get("media_title"),
            library_section=data.get("library_section"),
        )

        start_time = data.get("start_time")
        if start_time:
            try:
                session.start_time = datetime.fromisoformat(start_time)
            except (ValueError, TypeError):
                session.start_time = datetime.now()

        end_time = data.get("end_time")
        if end_time:
            try:
                session.end_time = datetime.fromisoformat(end_time)
            except (ValueError, TypeError):
                session.end_time = None

        session.was_terminated = bool(data.get("was_terminated", 0))

        return session
