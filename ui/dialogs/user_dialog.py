import json
import os
from PyQt5.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QMessageBox,
    QHeaderView,
    QGridLayout,
    QGroupBox,
    QLabel,
)
from PyQt5.QtCore import Qt
from data.database import PlexPatrolDB
from ui.widgets.phone_field import PhoneNumberEdit


class UserManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = PlexPatrolDB()
        self.setWindowTitle("Gestion des utilisateurs")
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Tableau des utilisateurs
        group_box = QGroupBox("Utilisateurs")
        group_layout = QVBoxLayout(group_box)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(8)
        self.users_table.setHorizontalHeaderLabels(
            [
                "Nom d'utilisateur",
                "Téléphone",
                "Flux max",
                "Liste blanche",
                "Sessions totales",
                "Streams arrêtés",
                "Dernière activité",
                "Actions",
            ]
        )
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        self.users_table.itemSelectionChanged.connect(self.on_user_selected)

        # Activer le tri du tableau
        self.users_table.setSortingEnabled(True)

        group_layout.addWidget(self.users_table)
        layout.addWidget(group_box)

        # Détails de l'utilisateur
        details_box = QGroupBox("Détails de l'utilisateur")
        form_layout = QGridLayout(details_box)

        # Ligne 1
        form_layout.addWidget(QLabel("Nom d'utilisateur:"), 0, 0)
        self.username_edit = QLineEdit()
        form_layout.addWidget(self.username_edit, 0, 1)

        form_layout.addWidget(QLabel("Nombre max de flux:"), 0, 2)
        self.max_streams_spin = QSpinBox()
        self.max_streams_spin.setRange(1, 10)
        form_layout.addWidget(self.max_streams_spin, 0, 3)

        # Ligne 2
        form_layout.addWidget(QLabel("E-mail:"), 1, 0)
        self.email_edit = QLineEdit()
        form_layout.addWidget(self.email_edit, 1, 1)

        form_layout.addWidget(QLabel("Téléphone:"), 1, 2)
        # Utiliser notre classe personnalisée pour le champ téléphone
        self.phone_edit = PhoneNumberEdit()
        self.phone_edit.setPlaceholderText("0601020304")
        form_layout.addWidget(self.phone_edit, 1, 3)

        # Ligne 3
        form_layout.addWidget(QLabel("Liste blanche:"), 2, 0)
        self.whitelist_check = QCheckBox()
        form_layout.addWidget(self.whitelist_check, 2, 1)

        # Ligne 4
        form_layout.addWidget(QLabel("Notes:"), 3, 0)
        self.notes_edit = QLineEdit()
        form_layout.addWidget(self.notes_edit, 3, 1, 1, 3)

        layout.addWidget(details_box)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        self.save_btn = QPushButton("Enregistrer les modifications")
        self.save_btn.clicked.connect(self.save_user)
        self.save_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_btn)

        refresh_btn = QPushButton("Actualiser")
        refresh_btn.clicked.connect(self.load_users)
        buttons_layout.addWidget(refresh_btn)

        migrate_btn = QPushButton("Migrer les données existantes")
        migrate_btn.clicked.connect(self.migrate_data)
        buttons_layout.addWidget(migrate_btn)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        # Ajout d'un bouton pour synchroniser avec Plex
        sync_btn = QPushButton("Synchroniser avec Plex")
        sync_btn.clicked.connect(self.sync_with_plex)
        buttons_layout.addWidget(sync_btn)

        layout.addLayout(buttons_layout)

        # Charger les utilisateurs
        self.load_users()

    def load_users(self):
        """Charger les utilisateurs depuis la base de données"""
        # Utiliser la nouvelle méthode qui récupère tous les utilisateurs
        users = self.db.get_all_users()

        # Désactiver temporairement le tri
        self.users_table.setSortingEnabled(False)

        self.users_table.setRowCount(0)

        for row, user in enumerate(users):
            # Accéder aux clés du dictionnaire plutôt qu'aux indices
            username = user.get("username", "Inconnu")
            user_id = user.get("id", "")
            phone = user.get("phone", "")
            max_streams = user.get("max_streams", 1)
            is_whitelisted = "Oui" if user.get("is_whitelisted", 0) else "Non"
            total_sessions = user.get("total_sessions", 0)
            kill_count = user.get("terminated_sessions", 0)
            last_activity = user.get("last_seen", "Jamais")

            self.users_table.insertRow(row)

            # Créer l'élément et stocker l'ID utilisateur
            username_item = QTableWidgetItem(username)
            username_item.setData(Qt.UserRole, user_id)
            self.users_table.setItem(row, 0, username_item)

            self.users_table.setItem(row, 1, QTableWidgetItem(phone))

            max_streams_item = QTableWidgetItem()
            max_streams_item.setData(Qt.DisplayRole, max_streams)
            self.users_table.setItem(row, 2, max_streams_item)

            self.users_table.setItem(row, 3, QTableWidgetItem(is_whitelisted))

            total_sessions_item = QTableWidgetItem()
            total_sessions_item.setData(Qt.DisplayRole, total_sessions)
            self.users_table.setItem(row, 4, total_sessions_item)

            kill_count_item = QTableWidgetItem()
            kill_count_item.setData(Qt.DisplayRole, kill_count)
            self.users_table.setItem(row, 5, kill_count_item)

            self.users_table.setItem(row, 6, QTableWidgetItem(last_activity))

            # Ajouter le bouton de suppression
            delete_button = QPushButton("Supprimer")
            delete_button.setProperty("username", username)
            delete_button.clicked.connect(self.delete_user)

            self.users_table.setCellWidget(row, 7, delete_button)

        # Réactiver le tri après avoir chargé toutes les données
        self.users_table.setSortingEnabled(True)

    def on_user_selected(self):
        """Réagir lorsqu'un utilisateur est sélectionné"""
        selected_rows = self.users_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            user_id = self.users_table.item(row, 0).data(Qt.UserRole)

            # Récupérer les détails complets de l'utilisateur
            user_details = self.db.get_user_details(user_id) if user_id else None

            if user_details:
                self.username_edit.setText(user_details.get("username", ""))
                self.max_streams_spin.setValue(user_details.get("max_streams", 1))
                self.whitelist_check.setChecked(
                    bool(user_details.get("is_whitelisted", 0))
                )
                self.email_edit.setText(user_details.get("email", "") or "")
                self.phone_edit.setText(user_details.get("phone", "") or "")
                self.notes_edit.setText(user_details.get("notes", "") or "")

                # Activer le bouton de sauvegarde
                self.save_btn.setEnabled(True)

    def save_user(self):
        """Enregistrer les modifications de l'utilisateur"""
        selected_rows = self.users_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            user_id = self.users_table.item(row, 0).data(Qt.UserRole)

            if user_id:
                username = self.username_edit.text()
                max_streams = self.max_streams_spin.value()
                is_whitelisted = int(self.whitelist_check.isChecked())
                email = self.email_edit.text()

                # S'assurer que le numéro de téléphone est correctement formaté avant de sauvegarder
                self.phone_edit.format_phone_number()
                phone = self.phone_edit.text()

                notes = self.notes_edit.text()

                # Mettre à jour dans la base de données
                if self.db.add_or_update_user(
                    user_id,
                    username,
                    email=email,
                    phone=phone,
                    is_whitelisted=is_whitelisted,
                    max_streams=max_streams,
                    notes=notes,
                ):
                    QMessageBox.information(
                        self, "Succès", "Utilisateur mis à jour avec succès!"
                    )
                    self.load_users()  # Recharger les données
                else:
                    QMessageBox.warning(
                        self, "Erreur", "Impossible de mettre à jour l'utilisateur"
                    )

    def delete_user(self):
        """Supprimer un utilisateur de la base de données et de la configuration"""
        sender = self.sender()
        username = sender.property("username")

        reply = QMessageBox.question(
            self,
            "Confirmation de suppression",
            f"Voulez-vous vraiment supprimer l'utilisateur '{username}'?\n"
            "Cette action supprimera également toutes ses statistiques associées.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                # Supprimer de la base de données
                self.db.delete_user(username)

                # Supprimer des statistiques si nécessaire
                if username in self.parent().stats:
                    del self.parent().stats[username]
                    from utils.helpers import get_app_path

                    stats_path = os.path.join(get_app_path(), "stats.json")
                    with open(stats_path, "w", encoding="utf-8") as f:
                        json.dump(self.parent().stats, f)

                # Recharger le tableau des utilisateurs
                self.load_users()

                QMessageBox.information(
                    self,
                    "Suppression réussie",
                    f"L'utilisateur '{username}' a été supprimé avec succès.",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur de suppression",
                    f"Une erreur s'est produite lors de la suppression de l'utilisateur: {str(e)}",
                )

    def migrate_data(self):
        """Migrer les données depuis les fichiers JSON vers la base de données"""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous migrer les données existantes vers la base de données?\n"
            "Cette opération peut prendre du temps en fonction du volume de données.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            from data.migration import migrate_data_to_db

            success = migrate_data_to_db()

            if success:
                QMessageBox.information(
                    self, "Succès", "Migration des données terminée!"
                )
                self.load_users()  # Recharger les utilisateurs
            else:
                QMessageBox.warning(
                    self, "Erreur", "Problème lors de la migration des données."
                )

    def sync_with_plex(self):
        """Synchronise les utilisateurs depuis Plex"""
        if not self.parent().plex_users:
            QMessageBox.warning(
                self,
                "Synchronisation impossible",
                "Aucun utilisateur Plex n'a été trouvé. Vérifiez votre connexion au serveur.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous synchroniser {len(self.parent().plex_users)} utilisateurs depuis Plex?\n"
            "Les utilisateurs existants seront conservés, mais leurs limites seront mises à jour si nécessaire.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Compteur d'utilisateurs ajoutés ou mis à jour
            updated_count = 0

            # Mettre à jour ou ajouter chaque utilisateur Plex directement dans la base de données
            for user_id, username in self.parent().plex_users.items():
                # Ajouter ou mettre à jour l'utilisateur dans la base de données
                success = self.db.add_or_update_user(
                    user_id=user_id,
                    username=username,
                    is_whitelisted=0,  # Par défaut, non whitelisté
                    max_streams=1,  # Valeur par défaut
                )

                if success:
                    updated_count += 1

            # Actualiser le tableau
            self.load_users()

            QMessageBox.information(
                self,
                "Synchronisation réussie",
                f"{updated_count} utilisateurs synchronisés avec Plex.",
            )
