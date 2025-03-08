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
from utils.constants import UIMessages, TableColumns, LogMessages


class UserManagementDialog(QDialog):
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db if db else PlexPatrolDB()
        self.setWindowTitle(UIMessages.USER_DIALOG_TITLE)
        self.setMinimumSize(1200, 700)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Tableau des utilisateurs
        group_box = QGroupBox(UIMessages.GROUP_USERS)
        group_layout = QVBoxLayout(group_box)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(9)
        self.users_table.setHorizontalHeaderLabels(TableColumns.USERS)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        self.users_table.itemSelectionChanged.connect(self.on_user_selected)

        # Activer le tri du tableau
        self.users_table.setSortingEnabled(True)

        # Activer l'édition directe sur double-clic dans le tableau
        self.users_table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )

        group_layout.addWidget(self.users_table)
        layout.addWidget(group_box)

        # Détails de l'utilisateur
        details_box = QGroupBox(UIMessages.GROUP_USER_DETAILS)
        form_layout = QGridLayout(details_box)

        # Ligne 1
        form_layout.addWidget(QLabel(UIMessages.LABEL_USERNAME), 0, 0)
        self.username_edit = QLineEdit()
        form_layout.addWidget(self.username_edit, 0, 1)

        form_layout.addWidget(QLabel(UIMessages.LABEL_MAX_STREAMS), 0, 2)
        self.max_streams_spin = QSpinBox()
        self.max_streams_spin.setRange(1, 10)
        form_layout.addWidget(self.max_streams_spin, 0, 3)

        # Ligne 2
        form_layout.addWidget(QLabel(UIMessages.LABEL_EMAIL), 1, 0)
        self.email_edit = QLineEdit()
        form_layout.addWidget(self.email_edit, 1, 1)

        form_layout.addWidget(QLabel(UIMessages.LABEL_PHONE), 1, 2)
        # Utiliser notre classe personnalisée pour le champ téléphone
        self.phone_edit = PhoneNumberEdit()
        self.phone_edit.setPlaceholderText(UIMessages.PLACEHOLDER_PHONE)
        form_layout.addWidget(self.phone_edit, 1, 3)

        # Ligne 3
        form_layout.addWidget(QLabel(UIMessages.LABEL_WHITELIST), 2, 0)
        self.whitelist_check = QCheckBox()
        form_layout.addWidget(self.whitelist_check, 2, 1)

        form_layout.addWidget(QLabel(UIMessages.LABEL_ACCOUNT_DISABLED), 2, 2)
        self.disabled_check = QCheckBox()
        form_layout.addWidget(self.disabled_check, 2, 3)

        # Ligne 4
        form_layout.addWidget(QLabel(UIMessages.LABEL_NOTES), 3, 0)
        self.notes_edit = QLineEdit()
        form_layout.addWidget(self.notes_edit, 3, 1, 1, 3)

        layout.addWidget(details_box)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        self.save_btn = QPushButton(UIMessages.BTN_SAVE)
        self.save_btn.clicked.connect(self.save_user)
        self.save_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_btn)

        refresh_btn = QPushButton(UIMessages.BTN_REFRESH)
        refresh_btn.clicked.connect(self.load_users)
        buttons_layout.addWidget(refresh_btn)

        close_btn = QPushButton(UIMessages.BTN_CLOSE)
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        # Ajout d'un bouton pour synchroniser avec Plex
        sync_btn = QPushButton(UIMessages.BTN_SYNC)
        sync_btn.clicked.connect(self.sync_with_plex)
        buttons_layout.addWidget(sync_btn)

        layout.addLayout(buttons_layout)

        # Charger les utilisateurs
        self.load_users()

    def load_users(self):
        """Charger les utilisateurs depuis la base de données"""
        # Désactiver la détection des changements pendant le chargement
        self._editing = False

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
            is_disabled = "Oui" if user.get("is_disabled", 0) else "Non"
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

            self.users_table.setItem(row, 4, QTableWidgetItem(is_disabled))

            total_sessions_item = QTableWidgetItem()
            total_sessions_item.setData(Qt.DisplayRole, total_sessions)
            self.users_table.setItem(row, 5, total_sessions_item)

            kill_count_item = QTableWidgetItem()
            kill_count_item.setData(Qt.DisplayRole, kill_count)
            self.users_table.setItem(row, 6, kill_count_item)

            self.users_table.setItem(row, 7, QTableWidgetItem(last_activity))

            # Ajouter le bouton de suppression
            delete_button = QPushButton("Supprimer")
            delete_button.setProperty("username", username)
            delete_button.clicked.connect(self.delete_user)

            self.users_table.setCellWidget(row, 8, delete_button)

        # Réactiver le tri après avoir chargé toutes les données
        self.users_table.setSortingEnabled(True)

        # Déconnecter l'ancien signal si existant pour éviter les connexions multiples
        try:
            self.users_table.itemChanged.disconnect(self.on_cell_edited)
        except:
            pass

        # Connecter le signal itemChanged une fois les données chargées
        self.users_table.itemChanged.connect(self.on_cell_edited)

        # Réactiver la détection des changements
        self._editing = True

        # Trier automatiquement par nom d'utilisateur (colonne 0) en ordre croissant
        self.users_table.sortItems(0, Qt.AscendingOrder)

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
                self.max_streams_spin.setValue(user_details.get("max_streams", 2))
                self.whitelist_check.setChecked(
                    bool(user_details.get("is_whitelisted", 0))
                )
                self.disabled_check.setChecked(bool(user_details.get("is_disabled", 0)))
                self.email_edit.setText(user_details.get("email", "") or "")
                self.phone_edit.setText(user_details.get("phone", "") or "")
                self.notes_edit.setText(user_details.get("notes", "") or "")

                # Activer le bouton de sauvegarde
                self.save_btn.setEnabled(True)

    def on_cell_edited(self, item):
        """Traite l'édition directe d'une cellule du tableau"""
        # Éviter le traitement pendant le chargement initial des données
        if not hasattr(self, "_editing"):
            return

        row = item.row()
        col = item.column()
        new_value = item.text()

        # Ignorer les colonnes non éditables (selon votre structure)
        # Colonnes 5, 6, 7 (total_sessions, kill_count, last_activity) ne devraient pas être éditables
        # Colonne 8 contient le bouton de suppression
        if col in [5, 6, 7, 8]:
            return

        user_id = self.users_table.item(row, 0).data(Qt.UserRole)
        username = self.users_table.item(row, 0).text()

        # Selon la colonne éditée, mettre à jour la valeur correspondante
        try:
            if col == 0:  # Nom d'utilisateur
                # Mettre à jour le nom d'utilisateur
                self.db.add_or_update_user(user_id, new_value)
            elif col == 1:  # Téléphone
                # Mettre à jour le numéro de téléphone
                self.db.add_or_update_user(user_id, username, phone=new_value)
            elif col == 2:  # Max Streams
                # S'assurer que c'est un nombre valide
                try:
                    max_streams = int(new_value)
                    if 1 <= max_streams <= 10:
                        self.db.add_or_update_user(
                            user_id, username, max_streams=max_streams
                        )
                    else:
                        raise ValueError("Le nombre de flux doit être entre 1 et 10")
                except ValueError:
                    # Restaurer l'ancienne valeur
                    item.setText(str(self.db.get_user_max_streams(user_id)))
                    return
            elif col == 3:  # Whitelist
                is_whitelisted = 1 if new_value.lower() == "oui" else 0
                self.db.set_user_whitelist_status(user_id, is_whitelisted)
                # Assurer une représentation cohérente
                item.setText("Oui" if is_whitelisted else "Non")
            elif col == 4:  # Disabled
                is_disabled = 1 if new_value.lower() == "oui" else 0
                self.db.set_user_disabled_status(user_id, is_disabled)
                # Assurer une représentation cohérente
                item.setText("Oui" if is_disabled else "Non")

            # No need to reload the entire table, just update the specific cell
        except Exception as e:
            QMessageBox.warning(
                self, "Erreur de mise à jour", f"Impossible de mettre à jour: {str(e)}"
            )
            # Reload the table to restore original values
            self.load_users()

    def save_user(self):
        """Enregistrer les modifications de l'utilisateur"""
        selected_rows = self.users_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            user_id = self.users_table.item(row, 0).data(Qt.UserRole)

            if user_id:
                username = self.username_edit.text()
                max_streams = self.max_streams_spin.value()
                is_whitelisted = self.whitelist_check.isChecked()
                is_disabled = self.disabled_check.isChecked()
                email = self.email_edit.text()

                # S'assurer que le numéro de téléphone est correctement formaté avant de sauvegarder
                self.phone_edit.format_phone_number()
                phone = self.phone_edit.text()

                notes = self.notes_edit.text()

                # Mettre à jour l'utilisateur avec les informations de base
                success = self.db.add_or_update_user(
                    user_id,
                    username,
                    email=email,
                    phone=phone,
                    notes=notes,
                    max_streams=max_streams,
                )

                # Mettre à jour spécifiquement les statuts whitelist et disabled
                if success:
                    whitelist_success = self.db.set_user_whitelist_status(
                        user_id, is_whitelisted
                    )
                    disabled_success = self.db.set_user_disabled_status(
                        user_id, is_disabled
                    )

                    if whitelist_success and disabled_success:
                        QMessageBox.information(
                            self, UIMessages.TITLE_SUCCESS, UIMessages.USER_UPDATED
                        )
                        self.load_users()  # Recharger les données
                    else:
                        QMessageBox.warning(
                            self, "Erreur", UIMessages.ERROR_UPDATE_USER
                        )
                else:
                    QMessageBox.warning(self, "Erreur", UIMessages.ERROR_UPDATE_USER)

    def delete_user(self):
        """Supprimer un utilisateur de la base de données et de la configuration"""
        sender = self.sender()
        username = sender.property("username")

        reply = QMessageBox.question(
            self,
            UIMessages.TITLE_CONFIRMATION,
            UIMessages.CONFIRM_DELETE_USER.format(username=username),
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
                    UIMessages.TITLE_SUCCESS,
                    UIMessages.USER_DELETED.format(username=username),
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur de suppression",
                    UIMessages.USER_DELETE_ERROR.format(error=str(e)),
                )

    def sync_with_plex(self):
        """Synchronise les utilisateurs depuis Plex"""
        if not self.parent().plex_users:
            QMessageBox.warning(
                self,
                "Synchronisation impossible",
                UIMessages.ERROR_NO_PLEX_USERS,
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            UIMessages.CONFIRM_SYNC_USERS.format(count=len(self.parent().plex_users)),
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
                    max_streams=2,  # Valeur par défaut
                )

                if success:
                    updated_count += 1

            # Actualiser le tableau
            self.load_users()

            QMessageBox.information(
                self,
                UIMessages.TITLE_SUCCESS,
                UIMessages.SYNC_SUCCESS.format(count=updated_count),
            )
