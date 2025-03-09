import os
import time
import json
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QStatusBar,
    QToolBar,
    QAction,
    QMessageBox,
    QGroupBox,
    QSystemTrayIcon,
    QMenu,
    QDialog,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QTextCursor

# Importer les modules personnalisés
from core import StreamMonitor
from data.database import PlexPatrolDB
from ui.dialogs import ConfigDialog, StatisticsDialog, MessageDialog
from config.config_manager import config
from utils import get_app_path
from utils.constants import (
    LogMessages,
    UIMessages,
    LogLevels,
    TableColumns,
    Paths,
    ConfigKeys,
)


class PlexPatrolApp(QMainWindow):
    """Interface graphique principale pour le moniteur de flux Plex"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(UIMessages.MAIN_WINDOW_TITLE)
        self.setWindowIcon(
            QIcon(os.path.join(get_app_path(), Paths.ASSETS, Paths.ICON))
        )
        self.resize(1400, 800)

        self._first_minimize = True

        # Ajouter le timer et le label pour le compteur de rafraîchissement
        self.refresh_counter_label = QLabel()
        self.refresh_counter_label.setAlignment(Qt.AlignRight)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_refresh_counter)
        self.last_poll_time = time.time()

        # Configuration initiale si nécessaire
        from config.config_manager import config

        if not config.first_time_setup():
            # Si l'utilisateur annule la configuration initiale, proposer de quitter
            reply = QMessageBox.question(
                self,
                "Configuration incomplète",
                UIMessages.CONFIG_INCOMPLETE,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                # Fermer immédiatement l'application
                self.close()
                return

        # Charger les statistiques
        self.stats = self.load_stats()

        # Charger les utilisateurs Plex
        self.plex_users = {}

        # Créer l'interface utilisateur
        self.setup_ui()

        # Charger les utilisateurs Plex
        self.load_plex_users()

        # Créer et démarrer le thread de surveillance
        self.stream_monitor = StreamMonitor()

        # Connecter les signaux
        self.stream_monitor.new_log.connect(self.add_log)
        self.stream_monitor.sessions_updated.connect(self.update_sessions_table)
        self.stream_monitor.connection_status.connect(self.update_connection_status)

        # Démarrer la surveillance
        self.stream_monitor.start()

        # Démarrer le timer maintenant que stream_monitor est initialisé
        self.refresh_timer.start(1000)  # Mise à jour chaque seconde

        # Configurer l'icône de la barre des tâches
        self.setup_tray_icon()

        # Ajouter le bouton "Minimiser dans le tray" dans la barre de titre
        self.setup_tray_minimize_button()

    def load_plex_users(self):
        """Charge la liste des utilisateurs Plex depuis le serveur"""
        try:
            from core.plex_api import get_plex_users

            self.plex_users = get_plex_users()
            if self.plex_users:
                self.add_log(
                    f"Chargement de {len(self.plex_users)} utilisateurs Plex réussi",
                    "SUCCESS",
                )
            else:
                self.add_log(
                    "Aucun utilisateur Plex trouvé ou erreur de connexion", "WARNING"
                )
        except Exception as e:
            self.add_log(
                f"Erreur lors du chargement des utilisateurs Plex: {str(e)}", "ERROR"
            )

    def setup_ui(self):
        """Configurer l'interface utilisateur"""
        # Widget central avec layout vertical
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Créer la barre d'outils
        self.create_toolbar()

        # Créer les onglets
        self.tabs = QTabWidget()

        # Onglet 1: Sessions actives
        sessions_tab = self.create_sessions_tab()

        # Onglet 2: Logs
        logs_tab = self.create_logs_tab()

        # Onglet 3: Statistiques
        stats_tab = self.create_stats_tab()

        # Ajouter les onglets au widget principal
        self.tabs.addTab(sessions_tab, "Sessions actives")
        self.tabs.addTab(logs_tab, "Journal des événements")
        self.tabs.addTab(stats_tab, "Statistiques")

        main_layout.addWidget(self.tabs)

        # Barre d'état
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_indicator = QLabel("■")
        self.status_indicator.setStyleSheet("color: green; font-size: 16px;")

        self.status_label = QLabel("Surveillance active")

        self.status_bar.addPermanentWidget(self.status_indicator)
        self.status_bar.addPermanentWidget(self.status_label)

    def create_toolbar(self):
        """Créer la barre d'outils"""
        toolbar = QToolBar("Actions principales")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Action pour démarrer/pauser la surveillance
        self.toggle_action = QAction("Pause", self)
        self.toggle_action.setCheckable(True)
        self.toggle_action.setStatusTip("Mettre en pause/reprendre la surveillance")
        self.toggle_action.triggered.connect(self.toggle_monitoring)
        toolbar.addAction(self.toggle_action)

        toolbar.addSeparator()

        # Action pour configurer le serveur
        config_action = QAction("Configuration", self)
        config_action.setStatusTip("Configurer les paramètres du serveur")
        config_action.triggered.connect(self.show_config_dialog)
        toolbar.addAction(config_action)

        # Action pour afficher les statistiques
        stats_action = QAction("Statistiques", self)
        stats_action.setStatusTip("Afficher les statistiques détaillées")
        stats_action.triggered.connect(self.show_stats_dialog)
        toolbar.addAction(stats_action)

        toolbar.addSeparator()

        # Action pour effacer les logs
        clear_logs_action = QAction("Effacer les logs", self)
        clear_logs_action.setStatusTip("Effacer les logs affichés")
        clear_logs_action.triggered.connect(self.clear_logs)
        toolbar.addAction(clear_logs_action)

        # Action pour gérer les utilisateurs
        users_action = QAction("Gérer les utilisateurs", self)
        users_action.setStatusTip("Gérer les utilisateurs et leurs permissions")
        users_action.triggered.connect(self.show_users_dialog)
        toolbar.addAction(users_action)

    def create_sessions_tab(self):
        """Créer l'onglet des sessions actives"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Ajouter le compteur de rafraîchissement en haut
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()  # Pour pousser le label à droite
        refresh_layout.addWidget(self.refresh_counter_label)
        layout.addLayout(refresh_layout)

        # Tableau des sessions actives
        sessions_group = QGroupBox(UIMessages.GROUP_ACTIVE_SESSIONS)
        group_layout = QVBoxLayout(sessions_group)

        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(8)

        # Définir les noms des colonnes (pour référence interne)
        self.column_names = [
            "Utilisateur",
            "Titre",
            "Section",
            "État",
            "Appareil",
            "Plateforme",
            "IP",
            "Actions",
        ]
        self.sessions_table.setHorizontalHeaderLabels(TableColumns.SESSIONS)

        # Configuration par défaut de la visibilité des colonnes (toutes visibles)
        self.column_visibility = [True] * len(self.column_names)

        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectRows)

        # Activer le tri
        self.sessions_table.setSortingEnabled(True)

        # Ajouter le menu contextuel pour l'en-tête
        self.sessions_table.horizontalHeader().setContextMenuPolicy(
            Qt.CustomContextMenu
        )
        self.sessions_table.horizontalHeader().customContextMenuRequested.connect(
            self.show_columns_menu
        )

        group_layout.addWidget(self.sessions_table)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.clicked.connect(self.refresh_sessions)
        buttons_layout.addWidget(self.refresh_btn)

        group_layout.addLayout(buttons_layout)

        layout.addWidget(sessions_group)

        # Styliser le compteur
        self.refresh_counter_label.setStyleSheet(
            """
            QLabel {
                color: #8a8a8a;
                font-size: 12px;
                padding: 5px;
            }
        """
        )

        return tab

    def show_columns_menu(self, position):
        """Afficher le menu contextuel pour montrer/cacher des colonnes"""
        menu = QMenu(self)
        menu.setTitle("Affichage des colonnes")

        # Ajouter une option pour chaque colonne (sauf "Actions" qui doit toujours être visible)
        for i, name in enumerate(
            self.column_names[:-1]
        ):  # Exclure la dernière colonne (Actions)
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(self.column_visibility[i])
            action.setData(i)  # Stocker l'index de la colonne
            action.triggered.connect(self.toggle_column_visibility)
            menu.addAction(action)

        # Afficher le menu à la position du curseur
        menu.exec_(
            self.sessions_table.horizontalHeader().viewport().mapToGlobal(position)
        )

    def toggle_column_visibility(self):
        """Basculer la visibilité d'une colonne"""
        action = self.sender()
        if action:
            column_index = action.data()
            is_visible = action.isChecked()

            # Mettre à jour l'état de visibilité
            self.column_visibility[column_index] = is_visible

            # Afficher ou masquer la colonne
            self.sessions_table.setColumnHidden(column_index, not is_visible)

            # Mettre à jour la mise en page du tableau
            self.sessions_table.horizontalHeader().resizeSections(QHeaderView.Stretch)

    def create_logs_tab(self):
        """Créer l'onglet des logs"""
        from ui.widgets.logs_widget import LogsWidget

        tab = QWidget()
        layout = QVBoxLayout(tab)
        logs_group = QGroupBox(UIMessages.GROUP_LOGS)
        logs_layout = QVBoxLayout(logs_group)
        logs_widget = LogsWidget()
        logs_layout.addWidget(logs_widget)
        layout.addWidget(logs_group)
        self.log_text = logs_widget.log_text  # Pour maintenir la compatibilité

        return tab

    def create_stats_tab(self):
        """Créer l'onglet des statistiques"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Tableau des statistiques
        stats_group = QGroupBox(UIMessages.GROUP_STATS)
        group_layout = QVBoxLayout(stats_group)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(
            [
                "Utilisateur",
                "Arrêts de flux",
                "Dernier arrêt",
                "Plateforme la plus utilisée",
                "Taux d'arrêts",
            ]
        )
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Activer le tri
        self.stats_table.setSortingEnabled(True)

        group_layout.addWidget(self.stats_table)

        layout.addWidget(stats_group)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        refresh_stats_btn = QPushButton("Rafraîchir")
        refresh_stats_btn.clicked.connect(self.refresh_stats)
        buttons_layout.addWidget(refresh_stats_btn)

        export_stats_btn = QPushButton("Exporter (CSV)")
        export_stats_btn.clicked.connect(self.export_stats)
        buttons_layout.addWidget(export_stats_btn)

        reset_stats_btn = QPushButton("Réinitialiser")
        reset_stats_btn.clicked.connect(self.reset_stats)
        buttons_layout.addWidget(reset_stats_btn)

        layout.addLayout(buttons_layout)

        return tab

    def setup_tray_icon(self):
        """Configurer l'icône de la barre des tâches"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(
            QIcon(os.path.join(get_app_path(), "assets", "plexpatrol_icon.png"))
        )

        # Créer le menu contextuel
        tray_menu = QMenu()

        show_action = QAction("Afficher", self)
        show_action.triggered.connect(self.show)

        toggle_action = QAction("Mettre en pause/Reprendre", self)
        toggle_action.triggered.connect(self.toggle_monitoring)

        quit_action = QAction("Quitter", self)
        quit_action.triggered.connect(self.close)

        tray_menu.addAction(show_action)
        tray_menu.addAction(toggle_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        """Gérer l'activation de l'icône de la barre des tâches"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()

    def hide(self):
        """Surcharge pour afficher un message lors de la première minimisation"""
        if hasattr(self, "_first_minimize") and self._first_minimize:
            self.tray_icon.showMessage(
                "PlexPatrol",
                "L'application continue de surveiller en arrière-plan.\nDouble-cliquez sur l'icône pour restaurer.",
                QSystemTrayIcon.Information,
                2000,
            )
            self._first_minimize = False
        super().hide()

    def add_log(self, message, level="INFO"):
        """Ajouter un message au journal des événements"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_message = f"[{current_time}] [{level}] {message}"

        # Définir la couleur en fonction du niveau
        color = "white"
        if level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "orange"
        elif level == "SUCCESS":
            color = "lightgreen"

        # Ajouter le message formaté
        self.log_text.append(f'<span style="color:{color};">{log_message}</span>')

        # Faire défiler vers le bas
        self.log_text.moveCursor(QTextCursor.End)

    def update_sessions_table(self, user_streams):
        """Mettre à jour le tableau des sessions actives"""
        # Désactiver le tri pendant le remplissage
        self.sessions_table.setSortingEnabled(False)
        self.sessions_table.setRowCount(0)

        row = 0
        for user_id, streams in user_streams.items():
            for stream in streams:
                self.sessions_table.insertRow(row)

                # Extraire les informations du stream
                (
                    session_id,
                    ip_address,
                    player_id,
                    library_section,
                    media_title,
                    platform,
                    product,
                    device,
                    username,
                    state,
                ) = stream

                # Ajouter les informations dans le tableau
                self.sessions_table.setItem(row, 0, QTableWidgetItem(username))
                self.sessions_table.setItem(row, 1, QTableWidgetItem(media_title))
                self.sessions_table.setItem(row, 2, QTableWidgetItem(library_section))
                self.sessions_table.setItem(row, 3, QTableWidgetItem(state))
                self.sessions_table.setItem(row, 4, QTableWidgetItem(device))
                self.sessions_table.setItem(row, 5, QTableWidgetItem(platform))
                self.sessions_table.setItem(row, 6, QTableWidgetItem(ip_address))

                # Ajouter un bouton pour arrêter le stream
                stop_button = QPushButton(UIMessages.BTN_STOP)
                stop_button.setProperty("session_id", session_id)
                stop_button.setProperty("username", username)
                stop_button.setProperty("state", state)
                stop_button.clicked.connect(self.stop_session)

                self.sessions_table.setCellWidget(row, 7, stop_button)

                row += 1

        # Réactiver le tri après le remplissage
        self.sessions_table.setSortingEnabled(True)

        # Appliquer les paramètres de visibilité des colonnes
        for i, is_visible in enumerate(self.column_visibility):
            self.sessions_table.setColumnHidden(i, not is_visible)

        # Mettre à jour le titre de l'onglet pour indiquer le nombre de sessions
        self.tabs.setTabText(0, f"Sessions actives ({row})")
        self.sessions_table.sortItems(0, Qt.AscendingOrder)

        # Réinitialiser le compteur de rafraîchissement
        self.reset_refresh_counter()

    def update_connection_status(self, is_connected):
        """Mettre à jour l'indicateur de connexion"""
        if is_connected:
            self.status_indicator.setStyleSheet("color: green; font-size: 16px;")
            self.status_label.setText("Surveillance active")
        else:
            self.status_indicator.setStyleSheet("color: red; font-size: 16px;")
            self.status_label.setText("Erreur de connexion")

    def toggle_monitoring(self):
        """Mettre en pause ou reprendre la surveillance"""
        is_paused = self.stream_monitor.toggle_pause()
        if is_paused:
            self.toggle_action.setText("Reprendre")
            self.status_indicator.setStyleSheet("color: orange; font-size: 16px;")
            self.status_label.setText("Surveillance en pause")
            # Arrêter le compteur
            self.refresh_timer.stop()
            self.refresh_counter_label.setText("Surveillance en pause")
        else:
            self.toggle_action.setText("Pause")
            self.status_indicator.setStyleSheet("color: green; font-size: 16px;")
            self.status_label.setText("Surveillance active")
            # Redémarrer le compteur
            self.reset_refresh_counter()

    def stop_session(self):
        """Arrêter une session spécifique avec un message personnalisé"""
        sender = self.sender()
        session_id = sender.property("session_id")
        username = sender.property("username")
        state = sender.property("state")  # Récupérer l'état du flux

        # Demander confirmation
        reply = QMessageBox.question(
            self,
            UIMessages.TITLE_CONFIRMATION,
            UIMessages.CONFIRM_SESSION_STOP.format(username=username),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Ouvrir le dialogue pour saisir le message
            dialog = MessageDialog(self)

            if dialog.exec_() == QDialog.Accepted:
                # Récupérer le message personnalisé
                custom_message = dialog.get_message()

                # Si le message est vide, utiliser un message par défaut
                if not custom_message:
                    if state == "paused":
                        custom_message = UIMessages.TERMINATION_MESSAGE_PAUSED
                    elif state == "playing":
                        custom_message = UIMessages.TERMINATION_MESSAGE_PLAYING
                    else:
                        custom_message = self.config.termination_message

                # Arrêter le flux avec le message personnalisé
                success = self.stream_monitor.stop_stream_with_message(
                    None, username, session_id, custom_message
                )

                if success:
                    self.add_log(
                        f"Session {session_id} arrêtée manuellement avec message personnalisé",
                        "SUCCESS",
                    )
                else:
                    self.add_log(
                        f"Échec de l'arrêt manuel de la session {session_id}", "ERROR"
                    )

                # Rafraîchir le tableau après quelques secondes
                QTimer.singleShot(5000, self.refresh_sessions)

    def refresh_sessions(self):
        """Forcer la mise à jour des sessions actives"""
        try:
            xml_data = self.stream_monitor.get_active_sessions()
            user_streams = self.stream_monitor.parse_sessions(xml_data)
            self.update_sessions_table(user_streams)
            self.add_log(UIMessages.SESSIONS_REFRESHED, LogLevels.INFO)
        except Exception as e:
            self.add_log(
                f"Erreur lors du rafraîchissement des sessions: {str(e)}", "ERROR"
            )

    def clear_logs(self):
        """Effacer les logs affichés"""
        self.log_text.clear()
        self.add_log("Journal effacé", "INFO")

    def save_logs(self):
        """Enregistrer les logs dans un fichier"""
        now = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        logs_path = os.path.join(get_app_path(), "logs")

        if not os.path.exists(logs_path):
            os.makedirs(logs_path)

        filepath = os.path.join(logs_path, f"PlexPatrol_logs_{now}.txt")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())

            self.add_log(f"Logs enregistrés dans {filepath}", "SUCCESS")
        except Exception as e:
            self.add_log(f"Erreur lors de l'enregistrement des logs: {str(e)}", "ERROR")

    def show_config_dialog(self):
        """Afficher la boîte de dialogue de configuration"""
        dialog = ConfigDialog(self)
        if dialog.exec_():
            self.add_log("Configuration mise à jour", "SUCCESS")

    def show_stats_dialog(self):
        """Afficher la boîte de dialogue des statistiques"""
        dialog = StatisticsDialog(self.stats, self)
        dialog.exec_()

    def refresh_stats(self):
        """Rafraîchir l'affichage des statistiques"""
        self.stats = self.load_stats()
        self.update_stats_table()
        self.add_log("Statistiques rafraîchies", "INFO")

    def load_stats(self):
        """Charger les statistiques depuis la base de données"""
        try:
            # Utiliser l'instance de DB déjà disponible via le moniteur si possible
            if hasattr(self, "stream_monitor") and hasattr(self.stream_monitor, "db"):
                db_instance = self.stream_monitor.db
            else:
                # Fallback si l'instance n'est pas disponible
                db_instance = PlexPatrolDB()

            stats_list = db_instance.get_user_stats()

            # Convertir la liste en dictionnaire avec username comme clé
            stats_dict = {}
            for user in stats_list:
                stats_dict[user["username"]] = user

            # IMPORTANT : retourner le dictionnaire pour que refresh_stats() fonctionne
            return stats_dict

        except Exception as e:
            self.add_log(
                f"Erreur lors du chargement des statistiques: {str(e)}", "ERROR"
            )
            return {}  # Retourner un dictionnaire vide en cas d'erreur

    def update_stats_table(self):
        """Mettre à jour le tableau des statistiques"""
        # Désactiver le tri pendant le remplissage
        self.stats_table.setSortingEnabled(False)

        self.stats_table.setRowCount(0)

        row = 0
        for username, data in self.stats.items():
            self.stats_table.insertRow(row)

            kill_count = data.get("kill_count", 0)
            last_kill = data.get("last_kill", "Jamais")

            # Trouver la plateforme la plus utilisée
            platforms = data.get("platforms", {})
            most_used = (
                max(platforms.items(), key=lambda x: x[1])[0]
                if platforms
                else "Inconnue"
            )

            # Calculer le taux d'arrêt
            total_sessions = data.get("total_sessions", 0)
            kill_rate = (
                f"{(kill_count / total_sessions) * 100:.1f}%"
                if total_sessions > 0
                else "N/A"
            )

            # Créer des QTableWidgetItem pour un tri correct
            username_item = QTableWidgetItem(username)

            kill_count_item = QTableWidgetItem()
            kill_count_item.setData(Qt.DisplayRole, kill_count)

            last_kill_item = QTableWidgetItem(last_kill)
            most_used_item = QTableWidgetItem(most_used)

            # Pour le taux d'arrêts, stocker la valeur numérique pour le tri
            kill_rate_item = QTableWidgetItem()
            if total_sessions > 0:
                # Stocker la valeur numérique pour le tri
                kill_rate_percent = (kill_count / total_sessions) * 100
                kill_rate_item.setData(Qt.DisplayRole, f"{kill_rate_percent:.1f}%")
                # Stocker la valeur brute pour le tri
                kill_rate_item.setData(Qt.UserRole, kill_rate_percent)
            else:
                kill_rate_item.setData(Qt.DisplayRole, "N/A")
                kill_rate_item.setData(Qt.UserRole, 0)  # Pour le tri

            self.stats_table.setItem(row, 0, username_item)
            self.stats_table.setItem(row, 1, kill_count_item)
            self.stats_table.setItem(row, 2, last_kill_item)
            self.stats_table.setItem(row, 3, most_used_item)
            self.stats_table.setItem(row, 4, kill_rate_item)

            row += 1

        # Réactiver le tri après le remplissage
        self.stats_table.setSortingEnabled(True)

        # Trier par défaut selon le nombre d'arrêts (colonne 1) en ordre décroissant
        self.stats_table.sortItems(0, Qt.AscendingOrder)

    def export_stats(self):
        """Exporter les statistiques au format CSV"""
        now = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        stats_path = os.path.join(get_app_path(), "exports")

        if not os.path.exists(stats_path):
            os.makedirs(stats_path)

        filepath = os.path.join(stats_path, f"PlexPatrol_stats_{now}.csv")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                # Écrire l'en-tête
                f.write(
                    "Utilisateur,Arrêts de flux,Dernier arrêt,Plateforme la plus utilisée,Taux d'arrêts\n"
                )

                # Écrire les données
                for username, data in self.stats.items():
                    kill_count = data.get("kill_count", 0)
                    last_kill = data.get("last_kill", "Jamais")

                    platforms = data.get("platforms", {})
                    most_used = (
                        max(platforms.items(), key=lambda x: x[1])[0]
                        if platforms
                        else "Inconnue"
                    )

                    total_sessions = data.get("total_sessions", 0)
                    kill_rate = (
                        f"{(kill_count / total_sessions) * 100:.1f}%"
                        if total_sessions > 0
                        else "N/A"
                    )

                    f.write(
                        f"{username},{kill_count},{last_kill},{most_used},{kill_rate}\n"
                    )

            self.add_log(
                UIMessages.STATS_EXPORTED.format(filepath=filepath), LogLevels.SUCCESS
            )
        except Exception as e:
            self.add_log(
                f"{LogMessages.STATS_EXPORT_ERROR.format(error=str(e))}",
                LogLevels.ERROR,
            )

    def reset_stats(self):
        """Réinitialiser les statistiques"""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous vraiment réinitialiser toutes les statistiques?\nCette action est irréversible.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.stats = {}
            stats_path = os.path.join(get_app_path(), "stats.json")

            try:
                with open(stats_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)

                self.update_stats_table()
                self.add_log("Statistiques réinitialisées", "SUCCESS")
            except Exception as e:
                self.add_log(
                    f"Erreur lors de la réinitialisation des statistiques: {str(e)}",
                    "ERROR",
                )

    def closeEvent(self, event):
        """Gérer la fermeture de l'application"""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous quitter l'application?\nLa surveillance sera arrêtée.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Masquer l'icône de la barre des tâches
            self.tray_icon.hide()

            # Arrêter proprement le thread de surveillance
            self.stream_monitor.stop()
            self.stream_monitor.wait(
                1000
            )  # Attendre jusqu'à 1 seconde que le thread se termine

            # Si le thread ne s'est pas terminé proprement, le forcer à s'arrêter
            if self.stream_monitor.isRunning():
                self.stream_monitor.terminate()
                self.stream_monitor.wait()

            # Fermer proprement la connexion à la base de données
            if hasattr(self.stream_monitor, "db"):
                # S'assurer que toutes les connexions à la base de données sont fermées
                try:
                    # Si PlexPatrolDB a une méthode de fermeture, l'utiliser
                    if hasattr(self.stream_monitor.db, "close"):
                        self.stream_monitor.db.close()
                except:
                    pass

            event.accept()
        else:
            event.ignore()

    def show_users_dialog(self):
        """Afficher la boîte de dialogue de gestion des utilisateurs"""
        from ui.dialogs.user_dialog import (
            UserManagementDialog,
        )  # Importation à la demande

        dialog = UserManagementDialog(self, db=self.stream_monitor.db)
        dialog.exec_()

    def update_refresh_counter(self):
        """Mettre à jour le compteur de rafraîchissement"""
        if (
            hasattr(self, "stream_monitor")
            and hasattr(self.stream_monitor, "last_poll_time")
            and not self.stream_monitor.is_paused
        ):
            elapsed = time.time() - self.stream_monitor.last_poll_time
            remaining = max(0, self.stream_monitor.config.check_interval - int(elapsed))
            self.refresh_counter_label.setText(
                f"Prochain rafraîchissement dans: {remaining}s"
            )
        else:
            self.refresh_counter_label.setText("Surveillance en pause")

    def reset_refresh_counter(self):
        """Réinitialiser le compteur après un rafraîchissement"""
        # Obtenir l'intervalle de vérification de la configuration
        check_interval = config.get(ConfigKeys.CHECK_INTERVAL, 30)
        self.refresh_counter = check_interval

        # Arrêter le timer s'il est en cours et le redémarrer
        self.refresh_timer.stop()
        self.refresh_timer.start(1000)  # Timer de 1 seconde

    def setup_tray_minimize_button(self):
        """Configure un bouton personnalisé pour minimiser dans le tray"""
        # Créer un widget pour contenir le bouton
        from PyQt5.QtWidgets import QToolButton, QStyle, QWidget, QHBoxLayout
        from PyQt5.QtCore import QSize, Qt

        # Créer une barre d'outils pour le bouton de minimisation dans le tray
        tray_toolbar = QToolBar("Tray Toolbar", self)
        tray_toolbar.setMovable(False)
        tray_toolbar.setFloatable(False)
        tray_toolbar.setIconSize(QSize(16, 16))

        # Créer un widget d'espacement qui pousse le bouton vers la droite
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tray_toolbar.addWidget(spacer)

        # Créer le bouton avec l'icône du tray
        self.tray_button = QToolButton(self)
        self.tray_button.setIcon(
            QIcon(os.path.join(get_app_path(), "assets", "minimize_tray.png"))
        )
        self.tray_button.setToolTip("Minimiser dans la zone de notification")
        self.tray_button.setFixedSize(QSize(30, 30))
        self.tray_button.clicked.connect(self.hide)

        # Ajouter le bouton après le spacer (donc aligné à droite)
        tray_toolbar.addWidget(self.tray_button)

        # Ajouter la barre d'outils en haut
        self.addToolBar(Qt.TopToolBarArea, tray_toolbar)
