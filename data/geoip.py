import os
import logging
from utils import get_app_path
import geoip2.database
from geoip2.errors import AddressNotFoundError


class GeoIPLocator:
    def __init__(self):
        # Créer le dossier geoip s'il n'existe pas
        geoip_dir = os.path.join(get_app_path(), "assets", "geoip")
        if not os.path.exists(geoip_dir):
            try:
                os.makedirs(geoip_dir, exist_ok=True)
            except Exception as e:
                logging.error(f"Impossible de créer le dossier geoip: {str(e)}")

        self.db_path = os.path.join(geoip_dir, "GeoLite2-City.mmdb")
        self.reader = None

        try:
            if os.path.exists(self.db_path):
                self.reader = geoip2.database.Reader(self.db_path)
                logging.info("Base de données GeoIP chargée avec succès")
            else:
                logging.warning(f"Base de données GeoIP non trouvée: {self.db_path}")
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation de GeoIP: {str(e)}")

    def locate_ip(self, ip_address):
        """
        Localiser une adresse IP

        Args:
            ip_address: Adresse IP à localiser

        Returns:
            dict: Dictionnaire contenant les informations de localisation
        """
        if not self.reader:
            return None

        if not ip_address or ip_address in ("127.0.0.1", "::1", "localhost"):
            return {
                "country": "Local",
                "city": "Réseau local",
                "latitude": 0,
                "longitude": 0,
            }

        try:
            response = self.reader.city(ip_address)
            return {
                "country": response.country.name,
                "country_code": response.country.iso_code,
                "city": response.city.name,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude,
            }
        except AddressNotFoundError:
            return {
                "country": "Inconnu",
                "city": "Adresse non trouvée",
                "latitude": 0,
                "longitude": 0,
            }
        except Exception as e:
            logging.error(
                f"Erreur lors de la localisation de l'IP {ip_address}: {str(e)}"
            )
            return None

    def close(self):
        """Fermer proprement le reader GeoIP"""
        if self.reader:
            self.reader.close()
