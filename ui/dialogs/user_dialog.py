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
    QComboBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from data.database import PlexPatrolDB
from ui.widgets.phone_field import PhoneNumberEdit
from utils.constants import UIMessages, TableColumns, LogMessages


class UserManagementDialog(QDialog):
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db if db else PlexPatrolDB()
        self.setWindowTitle(UIMessages.USER_DIALOG_TITLE)

        # Obtenir la taille de l'écran
        from PyQt5.QtWidgets import QDesktopWidget

        screen_size = QDesktopWidget().availableGeometry().size()

        # Calculer les dimensions (par exemple, 80% de la largeur et 70% de la hauteur)
        width = int(screen_size.width() * 0.6)
        height = int(screen_size.height() * 0.7)

        # Définir la taille minimale et la taille de départ
        self.setMinimumSize(900, 600)
        self.resize(width, height)  # Taille optimale au démarrage

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Tableau des utilisateurs
        group_box = QGroupBox(UIMessages.GROUP_USERS)
        group_layout = QVBoxLayout(group_box)

        # Ajouter une case à cocher pour afficher/masquer les utilisateurs désactivés
        filter_layout = QHBoxLayout()
        self.show_disabled_check = QCheckBox("Afficher les utilisateurs désactivés")
        self.show_disabled_check.setChecked(
            False
        )  # Par défaut, on n'affiche pas les désactivés
        self.show_disabled_check.toggled.connect(self.on_show_disabled_toggled)
        filter_layout.addWidget(self.show_disabled_check)
        filter_layout.addStretch(1)

        group_layout.addLayout(filter_layout)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(9)
        self.users_table.setHorizontalHeaderLabels(TableColumns.USERS)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.ExtendedSelection)
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

        refresh_btn = QPushButton(UIMessages.BTN_REFRESH)
        refresh_btn.clicked.connect(self.load_users)
        buttons_layout.addWidget(refresh_btn)

        bulk_edit_btn = QPushButton("Édition en masse")
        bulk_edit_btn.clicked.connect(self.bulk_edit_selected)
        buttons_layout.addWidget(bulk_edit_btn)

        self.save_btn = QPushButton(UIMessages.BTN_SAVE)
        self.save_btn.clicked.connect(self.save_user)
        self.save_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_btn)

        close_btn = QPushButton(UIMessages.BTN_CLOSE)
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        # Ajout d'un bouton pour synchroniser avec Plex
        sync_btn = QPushButton(UIMessages.BTN_SYNC)
        sync_btn.clicked.connect(self.sync_with_plex)
        buttons_layout.addWidget(sync_btn)

        layout.addLayout(buttons_layout)

        # Charger les utilisateurs
        self.load_users(include_disabled=False)

    def load_users(self, include_disabled=False):
        """Charger les utilisateurs depuis la base de données"""
        # Déconnecter l'ancien signal si existant pour éviter les connexions multiples
        try:
            self.users_table.itemChanged.disconnect(self.on_cell_edited)
        except:
            pass

        # Désactiver la détection des changements pendant le chargement
        self._editing = False

        # Utiliser la nouvelle méthode qui récupère tous les utilisateurs
        users = self.db.get_all_users(include_disabled=include_disabled)

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

            # Vérifier si l'utilisateur est désactivé
            if user.get("is_disabled", 0):
                for col in range(
                    self.users_table.columnCount() - 1
                ):  # Sauf le bouton supprimer
                    item = self.users_table.item(row, col)
                    item.setForeground(QBrush(QColor(128, 128, 128)))  # Texte grisé

        # Réactiver le tri après avoir chargé toutes les données
        self.users_table.setSortingEnabled(True)

        # Réactiver la détection des changements
        self._editing = True

        # Trier automatiquement par nom d'utilisateur (colonne 0) en ordre croissant
        self.users_table.sortItems(0, Qt.AscendingOrder)

        # Connecter le signal itemChanged une fois les données chargées
        self.users_table.itemChanged.connect(self.on_cell_edited)

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
        if not hasattr(self, "_editing") or not self._editing:
            return

        row = item.row()
        col = item.column()
        new_value = item.text()

        # Ignorer les colonnes non éditables
        if col in [5, 6, 7, 8]:
            return

        user_id = self.users_table.item(row, 0).data(Qt.UserRole)
        username = self.users_table.item(row, 0).text()

        try:
            # Le code existant pour traiter les différentes colonnes...

            # Pour la colonne "Disabled", ajouter cette logique spéciale
            if col == 4:  # Disabled
                is_disabled = (
                    1 if new_value.lower() in ["oui", "yes", "1", "true"] else 0
                )
                self.db.set_user_disabled_status(user_id, is_disabled)

                # Assurer une représentation cohérente avant le rechargement
                item.setText("Oui" if is_disabled else "Non")

                # Mémoriser la position de défilement
                scrollbar_pos = self.users_table.verticalScrollBar().value()

                # Recharger la liste avec le paramètre d'affichage actuel
                include_disabled = self.show_disabled_check.isChecked()
                self.load_users(include_disabled=include_disabled)

                # Restaurer la position de défilement
                self.users_table.verticalScrollBar().setValue(scrollbar_pos)
                return  # Sortir car la liste a été rechargée

        except Exception as e:
            QMessageBox.warning(
                self, "Erreur de mise à jour", f"Impossible de mettre à jour: {str(e)}"
            )
            # Recharger pour restaurer les valeurs d'origine
            self.load_users(include_disabled=self.show_disabled_check.isChecked())

    def on_show_disabled_toggled(self, checked):
        """Affiche ou masque les utilisateurs désactivés sans reconstruire tout le tableau"""
        # Désactiver temporairement le signal itemChanged pour éviter les effets en cascade
        try:
            self.users_table.itemChanged.disconnect(self.on_cell_edited)
        except:
            pass

        # Mémoriser la position de défilement
        scrollbar_pos = self.users_table.verticalScrollBar().value()

        # Charger les utilisateurs avec l'option d'affichage des désactivés
        self.load_users(include_disabled=checked)

        # Reconnecter le signal après le chargement
        self.users_table.itemChanged.connect(self.on_cell_edited)

        # Restaurer la position de défilement
        self.users_table.verticalScrollBar().setValue(scrollbar_pos)

    def bulk_edit_selected(self):
        """Modifier en masse les utilisateurs sélectionnés"""
        # Récupérer les lignes sélectionnées
        selected_items = self.users_table.selectedItems()

        if not selected_items:
            QMessageBox.warning(self, "Attention", "Aucun utilisateur sélectionné")
            return

        # Récupérer les lignes uniques (car selectedItems renvoie un item pour chaque cellule)
        selected_rows = set(item.row() for item in selected_items)

        # Créer une boîte de dialogue pour l'édition en masse
        dialog = QDialog(self)
        dialog.setWindowTitle("Édition en masse")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Options d'édition
        form_layout = QGridLayout()

        # Champs que l'utilisateur peut modifier en masse
        # Option Max Streams
        max_streams_check = QCheckBox("Modifier le nombre max de flux")
        form_layout.addWidget(max_streams_check, 0, 0)

        max_streams_spin = QSpinBox()
        max_streams_spin.setRange(1, 10)
        max_streams_spin.setValue(2)  # Valeur par défaut
        max_streams_spin.setEnabled(False)
        form_layout.addWidget(max_streams_spin, 0, 1)
        max_streams_check.toggled.connect(max_streams_spin.setEnabled)

        # Option Whitelist
        whitelist_check = QCheckBox("Modifier le statut whitelist")
        form_layout.addWidget(whitelist_check, 1, 0)

        whitelist_options = QComboBox()
        whitelist_options.addItems(["Non", "Oui"])
        whitelist_options.setEnabled(False)
        form_layout.addWidget(whitelist_options, 1, 1)
        whitelist_check.toggled.connect(whitelist_options.setEnabled)

        # Option Disabled
        disabled_check = QCheckBox("Modifier le statut désactivé")
        form_layout.addWidget(disabled_check, 2, 0)

        disabled_options = QComboBox()
        disabled_options.addItems(["Non", "Oui"])
        disabled_options.setEnabled(False)
        form_layout.addWidget(disabled_options, 2, 1)
        disabled_check.toggled.connect(disabled_options.setEnabled)

        layout.addLayout(form_layout)

        # Informations sur la sélection
        user_count_label = QLabel(f"{len(selected_rows)} utilisateur(s) sélectionné(s)")
        layout.addWidget(user_count_label)

        # Boutons
        buttons = QHBoxLayout()
        apply_btn = QPushButton("Appliquer")
        cancel_btn = QPushButton("Annuler")

        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)

        layout.addLayout(buttons)

        # Connexions
        cancel_btn.clicked.connect(dialog.reject)
        apply_btn.clicked.connect(dialog.accept)

        # Afficher la boîte de dialogue
        if dialog.exec_() == QDialog.Accepted:
            # Appliquer les modifications
            modified_count = 0

            for row in selected_rows:
                user_id = self.users_table.item(row, 0).data(Qt.UserRole)
                username = self.users_table.item(row, 0).text()

                changes_made = False

                # Modifier max_streams si demandé
                if max_streams_check.isChecked():
                    max_streams = max_streams_spin.value()
                    self.db.add_or_update_user(
                        user_id, username, max_streams=max_streams
                    )
                    self.users_table.item(row, 2).setData(Qt.DisplayRole, max_streams)
                    changes_made = True

                # Modifier whitelist si demandé
                if whitelist_check.isChecked():
                    is_whitelisted = whitelist_options.currentText() == "Oui"
                    self.db.set_user_whitelist_status(user_id, is_whitelisted)
                    self.users_table.item(row, 3).setText(
                        "Oui" if is_whitelisted else "Non"
                    )
                    changes_made = True

                # Modifier disabled si demandé
                if disabled_check.isChecked():
                    is_disabled = disabled_options.currentText() == "Oui"
                    self.db.set_user_disabled_status(user_id, is_disabled)
                    self.users_table.item(row, 4).setText(
                        "Oui" if is_disabled else "Non"
                    )
                    changes_made = True

                if changes_made:
                    modified_count += 1

            if modified_count > 0:
                QMessageBox.information(
                    self, "Succès", f"{modified_count} utilisateur(s) modifié(s)"
                )

    def save_user(self):
        """Enregistrer les modifications de l'utilisateur"""
        selected_rows = self.users_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            user_id = self.users_table.item(row, 0).data(Qt.UserRole)
            username = (
                self.username_edit.text()
            )  # Récupérer le nouveau nom d'utilisateur

            if user_id:
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
                        # Mémoriser la position de défilement
                        scrollbar_pos = self.users_table.verticalScrollBar().value()

                        # Recharger la liste avec le paramètre d'affichage actuel
                        include_disabled = self.show_disabled_check.isChecked()
                        self.load_users(include_disabled=include_disabled)

                        # Restaurer la position de défilement
                        self.users_table.verticalScrollBar().setValue(scrollbar_pos)

                        QMessageBox.information(
                            self, UIMessages.TITLE_SUCCESS, UIMessages.USER_UPDATED
                        )
                    else:
                        QMessageBox.warning(
                            self, "Erreur", UIMessages.ERROR_UPDATE_USER
                        )
                else:
                    QMessageBox.warning(self, "Erreur", UIMessages.ERROR_UPDATE_USER)

    def update_table_row(
        self, row, user_id, username, phone, max_streams, is_whitelisted, is_disabled
    ):
        """Met à jour uniquement la ligne concernée dans le tableau sans recharger tout le tableau"""
        # Désactiver temporairement le signal itemChanged pour éviter les effets en cascade
        try:
            self.users_table.itemChanged.disconnect(self.on_cell_edited)
        except:
            pass

        # Mettre à jour les cellules individuellement
        self.users_table.item(row, 0).setText(username)
        self.users_table.item(row, 1).setText(phone)

        max_streams_item = self.users_table.item(row, 2)
        max_streams_item.setData(Qt.DisplayRole, max_streams)

        self.users_table.item(row, 3).setText("Oui" if is_whitelisted else "Non")
        self.users_table.item(row, 4).setText("Oui" if is_disabled else "Non")

        # Réactiver le signal itemChanged
        self.users_table.itemChanged.connect(self.on_cell_edited)

        # S'assurer que la ligne reste sélectionnée
        self.users_table.selectRow(row)

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
