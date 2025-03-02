import sys
import os
import time
import yaml
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
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
    QFormLayout,
    QSplitter,
    QSystemTrayIcon,
    QMenu,
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QTextCursor, QPalette

# Importer les modules personnalisés
from stream_monitor import StreamMonitor
from config_dialog import ConfigDialog
from stats_dialog import StatisticsDialog
from utils import load_config, save_config, get_app_path
from dotenv import load_dotenv

# Recharger les variables d'environnement
load_dotenv(override=True)


class PlexMonitorApp(QMainWindow):
    """Interface graphique principale pour le moniteur de flux Plex"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlexPatrol - Moniteur de flux Plex")
        self.setWindowIcon(
            QIcon(os.path.join(get_app_path(), "assets", "plexpatrol_icon.png"))
        )
        self.resize(1400, 800)

        # Vérifier et initialiser le fichier .env si nécessaire
        from utils import initialize_env_file, validate_env_variables

        initialize_env_file()
        validate_env_variables()

        # Charger la configuration
        self.config = load_config()

        # Charger les statistiques
        self.stats = self.load_stats()

        # Créer l'interface utilisateur
        self.setup_ui()

        # Créer et démarrer le thread de surveillance
        self.stream_monitor = StreamMonitor(self.config)

        # Connecter les signaux
        self.stream_monitor.new_log.connect(self.add_log)
        self.stream_monitor.sessions_updated.connect(self.update_sessions_table)
        self.stream_monitor.connection_status.connect(self.update_connection_status)

        # Démarrer la surveillance
        self.stream_monitor.start()

        # Configurer l'icône de la barre des tâches
        self.setup_tray_icon()

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

    def create_sessions_tab(self):
        """Créer l'onglet des sessions actives"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Tableau des sessions actives
        group_box = QGroupBox("Sessions actives")
        group_layout = QVBoxLayout(group_box)

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
        self.sessions_table.setHorizontalHeaderLabels(self.column_names)

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

        layout.addWidget(group_box)

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
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Zone de texte pour les logs
        group_box = QGroupBox("Journal des événements")
        group_layout = QVBoxLayout(group_box)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: white;
                font-family: Consolas, Monaco, monospace;
                font-size: 10pt;
            }
        """
        )

        group_layout.addWidget(self.log_text)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        clear_btn = QPushButton("Effacer")
        clear_btn.clicked.connect(self.clear_logs)
        buttons_layout.addWidget(clear_btn)

        save_logs_btn = QPushButton("Enregistrer les logs")
        save_logs_btn.clicked.connect(self.save_logs)
        buttons_layout.addWidget(save_logs_btn)

        group_layout.addLayout(buttons_layout)

        layout.addWidget(group_box)

        return tab

    def create_stats_tab(self):
        """Créer l'onglet des statistiques"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Tableau des statistiques
        group_box = QGroupBox("Statistiques des arrêts de flux")
        group_layout = QVBoxLayout(group_box)

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

        layout.addWidget(group_box)

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
                stop_button = QPushButton("Arrêter")
                stop_button.setProperty("session_id", session_id)
                stop_button.setProperty("username", username)
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
        else:
            self.toggle_action.setText("Pause")
            self.status_indicator.setStyleSheet("color: green; font-size: 16px;")
            self.status_label.setText("Surveillance active")

    def stop_session(self):
        """Arrêter une session spécifique"""
        sender = self.sender()
        session_id = sender.property("session_id")
        username = sender.property("username")

        # Demander confirmation
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment arrêter la session de {username}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            success = self.stream_monitor.manual_stop_stream(None, username, session_id)
            if success:
                self.add_log(f"Session {session_id} arrêtée manuellement", "SUCCESS")
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
            self.add_log("Sessions rafraîchies manuellement", "INFO")
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
        dialog = ConfigDialog(self.config, self)
        if dialog.exec_():
            # La configuration a été modifiée, recharger
            self.config = load_config()
            self.stream_monitor.config = self.config
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
        """Charger les statistiques depuis le fichier"""
        stats_path = os.path.join(get_app_path(), "stats.json")
        if os.path.exists(stats_path):
            try:
                with open(stats_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.add_log(
                    f"Erreur lors du chargement des statistiques: {str(e)}", "ERROR"
                )

        return {}

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

            self.add_log(f"Statistiques exportées dans {filepath}", "SUCCESS")
        except Exception as e:
            self.add_log(
                f"Erreur lors de l'exportation des statistiques: {str(e)}", "ERROR"
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
            self.tray_icon.hide()
            self.stream_monitor.stop()
            event.accept()
        else:
            event.ignore()


def main():
    """Point d'entrée principal"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Style moderne et cohérent

    # Appliquer une palette sombre
    apply_dark_palette(app)

    window = PlexMonitorApp()
    window.show()

    sys.exit(app.exec_())


def apply_dark_palette(app):
    """Appliquer un thème sombre à l'application"""
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(dark_palette)

    # Styles supplémentaires
    app.setStyleSheet(
        """
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        QPushButton {
            padding: 6px 12px;
            border-radius: 4px;
            background-color: #2a82da;
            color: white;
        }
        QPushButton:hover {
            background-color: #3a92ea;
        }
        QPushButton:pressed {
            background-color: #1a72ca;
        }
        QTableWidget {
            border: 1px solid #444444;
            gridline-color: #444444;
        }
        QHeaderView::section {
            background-color: #2a82da;
            color: white;
            padding: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #444444;
        }
        QTabBar::tab {
            background-color: #353535;
            padding: 8px 16px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            color: white;
        }
        QTabBar::tab:selected {
            background-color: #2a82da;
        }
        QGroupBox {
            border: 1px solid #444444;
            border-radius: 4px;
            margin-top: 1em;
            padding: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
            background-color: #353535;
        }
    """
    )


if __name__ == "__main__":
    main()
