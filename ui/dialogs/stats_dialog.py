from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QWidget,
    QGroupBox,
    QHBoxLayout,
    QRadioButton,
    QDateEdit,
    QLabel,
)
from PyQt5.QtChart import (
    QChart,
    QChartView,
    QPieSeries,
    QPieSlice,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt, QDate

from data.database import PlexPatrolDB
from utils.constants import UIMessages


class PercentageTableItem(QTableWidgetItem):
    """Item de tableau spécialisé pour les pourcentages avec tri correct"""

    def __init__(self, text, value):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        # Cette méthode est appelée lors du tri
        if isinstance(other, PercentageTableItem):
            return self.value < other.value
        return super().__lt__(other)


class StatisticsDialog(QDialog):
    """Dialogue d'affichage des statistiques détaillées"""

    def __init__(self, stats, db_instance=None, parent=None):
        super().__init__(parent)
        self.stats = stats
        self.db = db_instance if db_instance is not None else PlexPatrolDB()
        self.setWindowTitle("Statistiques détaillées")
        self.setMinimumSize(1200, 1000)
        self.initial_period = {"days": 7}
        self.setup_ui()

    def setup_ui(self):
        """Configurer l'interface utilisateur"""
        layout = QVBoxLayout(self)

        # Ajouter un sélecteur de période en haut du dialogue
        period_widget = self.create_period_selector()
        layout.addWidget(period_widget)

        # Créer les onglets pour les différents types de statistiques
        tabs = QTabWidget()

        # Onglets existants
        data_tab = self.create_data_tab(self.initial_period)
        tabs.addTab(data_tab, UIMessages.TAB_DATA)

        chart_tab = self.create_chart_tab(self.initial_period)
        tabs.addTab(chart_tab, UIMessages.TAB_CHARTS)

        platform_tab = self.create_platform_tab(self.initial_period)
        tabs.addTab(platform_tab, UIMessages.TAB_PLATFORMS)

        # Nouvel onglet: Tendances temporelles
        trends_tab = self.create_trends_tab(self.initial_period)
        tabs.addTab(trends_tab, "Tendances")

        # Nouvel onglet: Géolocalisation
        geo_tab = self.create_geolocation_tab(self.initial_period)
        tabs.addTab(geo_tab, "Géolocalisation IP")

        # Nouvel onglet: Appareils
        device_tab = self.create_device_tab(self.initial_period)
        tabs.addTab(device_tab, "Appareils")

        layout.addWidget(tabs)

        # Bouton de fermeture
        close_button = QPushButton(UIMessages.BTN_CLOSE)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)

    def create_period_selector(self):
        """Créer un widget pour la sélection de période"""

        # Créer un groupe pour le sélecteur de période
        group_box = QGroupBox("Période d'analyse")
        layout = QHBoxLayout(group_box)

        # Option pour les 7 derniers jours (défaut)
        self.radio_7_days = QRadioButton("7 derniers jours")
        self.radio_7_days.setChecked(True)
        layout.addWidget(self.radio_7_days)

        # Option pour les 30 derniers jours
        self.radio_30_days = QRadioButton("30 derniers jours")
        layout.addWidget(self.radio_30_days)

        # Option pour les 90 derniers jours
        self.radio_90_days = QRadioButton("90 derniers jours")
        layout.addWidget(self.radio_90_days)

        # Option pour une période personnalisée
        self.radio_custom = QRadioButton("Personnalisée:")
        layout.addWidget(self.radio_custom)

        # Date de début
        layout.addWidget(QLabel("Du"))
        self.date_start = QDateEdit(QDate.currentDate().addDays(-7))
        self.date_start.setCalendarPopup(True)
        layout.addWidget(self.date_start)

        # Date de fin
        layout.addWidget(QLabel("au"))
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        layout.addWidget(self.date_end)

        # Bouton d'application
        apply_btn = QPushButton("Appliquer")
        apply_btn.clicked.connect(self.refresh_stats)
        layout.addWidget(apply_btn)

        # Connecter les boutons radio pour activer/désactiver les sélecteurs de date
        self.radio_7_days.toggled.connect(self.update_date_selector_state)
        self.radio_30_days.toggled.connect(self.update_date_selector_state)
        self.radio_90_days.toggled.connect(self.update_date_selector_state)
        self.radio_custom.toggled.connect(self.update_date_selector_state)

        # État initial des sélecteurs de date
        self.update_date_selector_state()

        return group_box

    def update_date_selector_state(self):
        """Mettre à jour l'état des sélecteurs de date en fonction du choix de période"""
        custom_selected = self.radio_custom.isChecked()
        self.date_start.setEnabled(custom_selected)
        self.date_end.setEnabled(custom_selected)

        # Mettre à jour les dates par défaut selon l'option sélectionnée
        today = QDate.currentDate()
        if self.radio_7_days.isChecked():
            self.date_start.setDate(today.addDays(-7))
            self.date_end.setDate(today)
        elif self.radio_30_days.isChecked():
            self.date_start.setDate(today.addDays(-30))
            self.date_end.setDate(today)
        elif self.radio_90_days.isChecked():
            self.date_start.setDate(today.addDays(-90))
            self.date_end.setDate(today)

    def get_selected_period(self):
        """Obtenir la période sélectionnée en jours ou comme tuple de dates"""
        if self.radio_7_days.isChecked():
            return {"days": 7}
        elif self.radio_30_days.isChecked():
            return {"days": 30}
        elif self.radio_90_days.isChecked():
            return {"days": 90}
        else:  # Période personnalisée
            start_date = self.date_start.date().toString("yyyy-MM-dd")
            end_date = self.date_end.date().toString("yyyy-MM-dd")
            return {"start_date": start_date, "end_date": end_date}

    def refresh_stats(self):
        """Rafraîchir les statistiques avec la période sélectionnée"""
        # Obtenir la période sélectionnée
        period = self.get_selected_period()

        # Mettre à jour les données pour tous les onglets
        tabs = self.findChild(QTabWidget)
        if tabs:
            current_index = tabs.currentIndex()

            # Recréer les onglets avec les nouvelles données
            # Suppression des anciens onglets
            while tabs.count() > 0:
                tabs.removeTab(0)

            # Recréation des onglets avec les nouvelles données
            data_tab = self.create_data_tab(period)
            tabs.addTab(data_tab, UIMessages.TAB_DATA)

            chart_tab = self.create_chart_tab(period)
            tabs.addTab(chart_tab, UIMessages.TAB_CHARTS)

            platform_tab = self.create_platform_tab(period)
            tabs.addTab(platform_tab, UIMessages.TAB_PLATFORMS)

            trends_tab = self.create_trends_tab(period)
            tabs.addTab(trends_tab, "Tendances")

            geo_tab = self.create_geolocation_tab(period)
            tabs.addTab(geo_tab, "Géolocalisation IP")

            device_tab = self.create_device_tab(period)
            tabs.addTab(device_tab, "Appareils")

            # Restaurer l'onglet actif
            tabs.setCurrentIndex(current_index)

    def enable_sorting_for_table(self, table):
        """Active le tri pour un tableau"""
        # Activer le tri
        table.setSortingEnabled(True)

        # Configurer pour que le tri se fasse au clic sur l'en-tête
        table.horizontalHeader().setSectionsClickable(True)

        # Définir l'ordre de tri par défaut sur la première colonne, descendant
        table.sortItems(0, Qt.AscendingOrder)

    def create_data_tab(self, period=None):
        """Créer l'onglet avec le tableau de données"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Si période spécifiée, récupérer les stats en fonction de cette période
        if period is not None:
            if "days" in period:
                self.stats = self.db.get_user_stats(days=period["days"])
            else:
                self.stats = self.db.get_user_stats(
                    start_date=period["start_date"], end_date=period["end_date"]
                )

        # Tableau détaillé
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            [
                "Utilisateur",
                "Total sessions",
                "Streams arrêtés",
                "Dernière activité",
                "Taux d'arrêt",
            ]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Remplir le tableau
        row = 0
        for username, data in self.stats.items():
            table.insertRow(row)

            total_sessions = data.get("total_sessions", 0)
            kill_count = data.get("kill_count", 0)
            last_seen = data.get("last_seen", "Jamais")

            # Calculer le taux d'arrêt
            kill_rate = (
                f"{(kill_count / total_sessions) * 100:.1f}%"
                if total_sessions > 0
                else "N/A"
            )

            # Ajouter les données au tableau
            table.setItem(row, 0, QTableWidgetItem(username))

            # Utiliser des éléments numériques pour les colonnes sessions et kills
            sessions_item = QTableWidgetItem()
            sessions_item.setData(Qt.DisplayRole, total_sessions)
            table.setItem(row, 1, sessions_item)

            kills_item = QTableWidgetItem()
            kills_item.setData(Qt.DisplayRole, kill_count)
            table.setItem(row, 2, kills_item)

            # Date de dernière activité
            table.setItem(row, 3, QTableWidgetItem(last_seen))

            # Utiliser la classe personnalisée pour le taux d'arrêt
            rate_value = (
                (kill_count / total_sessions) * 100 if total_sessions > 0 else 0
            )
            rate_item = PercentageTableItem(kill_rate, rate_value)
            table.setItem(row, 4, rate_item)

            row += 1

        # Activer le tri pour ce tableau
        self.enable_sorting_for_table(table)

        # Configurer le tri initial par la colonne "Streams arrêtés" (colonne 2) par ordre décroissant
        table.sortItems(2, Qt.DescendingOrder)

        layout.addWidget(table)
        return tab

    def create_chart_tab(self, period=None):
        """Créer l'onglet avec les graphiques"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Déterminer le titre en fonction de la période
        if period is None or ("days" in period and period["days"] == 7):
            title = UIMessages.CHART_SESSIONS_TITLE + " (7 derniers jours)"
        elif "days" in period:
            title = (
                f"{UIMessages.CHART_SESSIONS_TITLE} ({period['days']} derniers jours)"
            )
        else:
            title = f"{UIMessages.CHART_SESSIONS_TITLE} ({period['start_date']} à {period['end_date']})"

        # Créer un graphique en camembert pour la répartition des arrêts
        pie_chart = QChart()
        pie_chart.setTitle(title)
        pie_chart.setAnimationOptions(QChart.SeriesAnimations)

        # Créer la série pour le camembert
        pie_series = QPieSeries()

        # Ajouter les données de chaque utilisateur
        total_kills = 0
        for username, data in self.stats.items():
            kill_count = data.get("kill_count", 0)
            total_kills += kill_count

        if total_kills > 0:
            for username, data in self.stats.items():
                kill_count = data.get("kill_count", 0)
                if kill_count > 0:
                    slice = pie_series.append(f"{username} ({kill_count})", kill_count)
                    slice.setLabelVisible(True)
        else:
            # Si aucun arrêt n'a été enregistré
            pie_series.append("Aucun arrêt", 1)

        pie_chart.addSeries(pie_series)

        # Afficher le camembert
        pie_view = QChartView(pie_chart)
        pie_view.setRenderHint(QPainter.Antialiasing)

        layout.addWidget(pie_view)

        return tab

    def create_platform_tab(self, period=None):
        """Créer l'onglet d'analyse par plateforme"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Créer un graphique en barres pour les plateformes
        bar_chart = QChart()
        if period is None or ("days" in period and period["days"] == 7):
            bar_chart.setTitle(UIMessages.CHART_PLATFORMS_TITLE + " (7 derniers jours)")
        elif "days" in period:
            bar_chart.setTitle(
                f"{UIMessages.CHART_PLATFORMS_TITLE} ({period['days']} derniers jours)"
            )
        else:
            bar_chart.setTitle(
                f"{UIMessages.CHART_PLATFORMS_TITLE} ({period['start_date']} à {period['end_date']})"
            )
        bar_chart.setAnimationOptions(QChart.SeriesAnimations)

        # Collecter les données par plateforme
        platforms = {}
        for username, data in self.stats.items():
            user_platforms = data.get("platforms", {})
            for platform, count in user_platforms.items():
                if platform not in platforms:
                    platforms[platform] = 0
                platforms[platform] += count

        # Créer la série de barres
        bar_series = QBarSeries()
        bar_set = QBarSet("Nombre d'arrêts")

        # Listes pour les axes
        platform_names = []

        # Ajouter les données
        for platform, count in sorted(
            platforms.items(), key=lambda x: x[1], reverse=True
        ):
            platform_names.append(platform)
            bar_set.append(count)

        bar_series.append(bar_set)
        bar_chart.addSeries(bar_series)

        # Configurer les axes
        axis_x = QBarCategoryAxis()
        axis_x.append(platform_names)
        bar_chart.addAxis(axis_x, Qt.AlignBottom)
        bar_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        max_value = max(platforms.values()) if platforms else 0
        axis_y.setRange(0, max_value + 1)
        bar_chart.addAxis(axis_y, Qt.AlignLeft)
        bar_series.attachAxis(axis_y)

        # Afficher le graphique en barres
        bar_view = QChartView(bar_chart)
        bar_view.setRenderHint(QPainter.Antialiasing)

        layout.addWidget(bar_view)

        # Tableau des plateformes
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Plateforme", "Arrêts de flux"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Remplir le tableau
        row = 0
        for platform, count in sorted(
            platforms.items(), key=lambda x: x[1], reverse=True
        ):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(platform))
            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, count)
            table.setItem(row, 1, item)

            row += 1

        self.enable_sorting_for_table(table)

        # Configurer le tri initial par la colonne "Arrêts de flux" (colonne 1) par ordre décroissant
        table.sortItems(1, Qt.DescendingOrder)

        layout.addWidget(table)

        return tab

    def create_trends_tab(self, period=None):
        """Créer l'onglet d'analyse des tendances temporelles"""
        from PyQt5.QtChart import QLineSeries, QDateTimeAxis, QValueAxis
        from datetime import datetime
        import logging

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Utiliser la période spécifiée ou par défaut 7 jours
        if period is None:
            period = {"days": 7}

        # Récupérer les données de sessions avec horodatage selon la période
        if "days" in period:
            sessions_by_time = self.db.get_sessions_by_time(days=period["days"])
        else:
            sessions_by_time = self.db.get_sessions_by_time_range(
                start_date=period["start_date"], end_date=period["end_date"]
            )

        # Vérifier si nous avons des données
        if not sessions_by_time:
            # Ajouter un message si aucune donnée n'est disponible
            empty_label = QLabel(
                "Aucune donnée disponible pour la période sélectionnée"
            )
            empty_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty_label)
            return tab

        # Créer un graphique pour l'utilisation au fil du temps
        time_chart = QChart()
        if period is None or ("days" in period and period["days"] == 7):
            time_chart.setTitle("Utilisation par jour et heure (7 derniers jours)")
        elif "days" in period:
            time_chart.setTitle(
                f"Utilisation par jour et heure ({period['days']} derniers jours)"
            )
        else:
            time_chart.setTitle(
                f"Utilisation par jour et heure ({period['start_date']} à {period['end_date']})"
            )
        time_chart.setAnimationOptions(QChart.SeriesAnimations)

        # Créer une série pour chaque type d'information
        series_started = QLineSeries()
        series_started.setName("Sessions démarrées")

        series_terminated = QLineSeries()
        series_terminated.setName("Sessions arrêtées")

        # Regrouper par jour
        days_data = {}
        for session in sessions_by_time:
            try:
                # Gérer les deux formats possibles (avec ou sans T)
                start_time = session["start_time"]

                # Extraire seulement la partie date (YYYY-MM-DD)
                if "T" in start_time:
                    date_str = start_time.split("T")[0]  # Format ISO
                else:
                    date_str = start_time.split()[0]  # Format avec espace

                if date_str not in days_data:
                    days_data[date_str] = {"started": 0, "terminated": 0}

                days_data[date_str]["started"] += 1
                if session["was_terminated"]:
                    days_data[date_str]["terminated"] += 1
            except (IndexError, KeyError, TypeError) as e:
                # Si format incorrect, ignorer cette entrée et continuer
                logging.warning(
                    f"Format de date non reconnu: {session.get('start_time', 'N/A')} - {str(e)}"
                )
                continue

        # Créer les points de données pour les graphiques
        for date_str, counts in sorted(days_data.items()):
            # Convertir en timestamp pour QDateTime
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            timestamp = dt.timestamp() * 1000  # En millisecondes pour Qt

            series_started.append(timestamp, counts["started"])
            series_terminated.append(timestamp, counts["terminated"])

        # Ajouter les séries au graphique
        time_chart.addSeries(series_started)
        time_chart.addSeries(series_terminated)

        # Configurer les axes
        axis_x = QDateTimeAxis()
        axis_x.setTickCount(7)
        axis_x.setFormat("dd/MM")
        axis_x.setTitleText("Date")
        time_chart.addAxis(axis_x, Qt.AlignBottom)
        series_started.attachAxis(axis_x)
        series_terminated.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Nombre de sessions")
        max_value = (
            max(
                [
                    max(data["started"], data["terminated"])
                    for data in days_data.values()
                ]
            )
            if days_data
            else 0
        )
        axis_y.setRange(0, max_value + 2)
        time_chart.addAxis(axis_y, Qt.AlignLeft)
        series_started.attachAxis(axis_y)
        series_terminated.attachAxis(axis_y)

        # Afficher le graphique
        time_view = QChartView(time_chart)
        time_view.setRenderHint(QPainter.Antialiasing)

        layout.addWidget(time_view)

        # Ajouter un graphique d'utilisation par heure de la journée
        hour_chart = self.create_hourly_usage_chart(sessions_by_time)
        hour_view = QChartView(hour_chart)
        hour_view.setRenderHint(QPainter.Antialiasing)

        layout.addWidget(hour_view)

        return tab

    def create_hourly_usage_chart(self, sessions_by_time):
        """Créer un graphique montrant l'utilisation par heure de la journée"""
        from PyQt5.QtChart import QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis

        # Graphique des heures
        hour_chart = QChart()
        hour_chart.setTitle("Utilisation par heure de la journée")
        hour_chart.setAnimationOptions(QChart.SeriesAnimations)

        # Initialiser les compteurs d'heure
        hours_data = {hour: 0 for hour in range(24)}

        # Compter les sessions par heure
        for session in sessions_by_time:
            try:
                start_time = session["start_time"]

                # Extraire l'heure selon le format
                if "T" in start_time:
                    # Format ISO: 2023-01-01T13:45:30.123456
                    hour_part = start_time.split("T")[1].split(":")[0]
                else:
                    # Format avec espace: 2023-01-01 13:45:30
                    hour_part = start_time.split()[1].split(":")[0]

                hour = int(hour_part)
                hours_data[hour] += 1
            except (IndexError, ValueError, KeyError, TypeError):
                continue

        # Reste du code inchangé...
        # Créer la série
        bar_set = QBarSet("Sessions")
        for hour in range(24):
            bar_set.append(hours_data[hour])

        # Créer la série de barres
        hour_series = QBarSeries()
        hour_series.append(bar_set)
        hour_chart.addSeries(hour_series)

        # Configurer les axes
        axis_x = QBarCategoryAxis()
        hour_labels = [f"{h}h" for h in range(24)]
        axis_x.append(hour_labels)
        hour_chart.addAxis(axis_x, Qt.AlignBottom)
        hour_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        max_value = max(hours_data.values()) if hours_data else 0
        axis_y.setRange(0, max_value + 1)
        axis_y.setTitleText("Nombre de sessions")
        hour_chart.addAxis(axis_y, Qt.AlignLeft)
        hour_series.attachAxis(axis_y)

        return hour_chart

    def create_device_tab(self, period=None):
        """Créer un onglet pour analyser les appareils les plus utilisés"""
        from PyQt5.QtGui import QFontMetrics
        from PyQt5.QtWidgets import QSplitter, QSizePolicy

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Créer un séparateur vertical pour contrôler la proportion entre graphique et tableau
        splitter = QSplitter(Qt.Vertical)

        # Conteneur pour le graphique
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)

        # Récupérer les statistiques sur les appareils
        if period is None:
            device_stats = self.db.get_device_stats()
        elif "days" in period:
            device_stats = self.db.get_device_stats(days=period["days"])
        else:
            device_stats = self.db.get_device_stats(
                start_date=period["start_date"], end_date=period["end_date"]
            )

        # Créer un graphique en camembert pour les appareils
        pie_chart = QChart()
        if period is None or ("days" in period and period["days"] == 7):
            pie_chart.setTitle("Répartition des appareils utilisés (7 derniers jours)")
        elif "days" in period:
            pie_chart.setTitle(
                f"Répartition des appareils utilisés ({period['days']} derniers jours)"
            )
        else:
            pie_chart.setTitle(
                f"Répartition des appareils utilisés ({period['start_date']} à {period['end_date']})"
            )
        pie_chart.setAnimationOptions(QChart.SeriesAnimations)

        # Créer la série pour le camembert
        pie_series = QPieSeries()

        # Fonction pour formater le nom de l'appareil sur plusieurs lignes si nécessaire
        def format_device_name(device_name, count, max_length=20):
            # Diviser en mots pour éviter de couper au milieu d'un mot
            words = device_name.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line + " " + word) <= max_length:
                    current_line += (" " if current_line else "") + word
                else:
                    lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            # Ajouter le compte sur une nouvelle ligne
            lines.append(f"({count})")

            # Joindre avec des sauts de ligne
            return "\n".join(lines)

        # Ajouter les données
        for device in device_stats:
            device_name = device["device"] if device["device"] else "Inconnu"
            count = device["count"]
            if count > 0:
                formatted_name = format_device_name(device_name, count)
                slice = pie_series.append(formatted_name, count)
                slice.setLabelVisible(True)

                # Ajuster la position de l'étiquette
                slice.setLabelPosition(QPieSlice.LabelOutside)

        pie_chart.addSeries(pie_series)
        pie_chart.legend().setVisible(
            False
        )  # Cacher la légende pour éviter la duplication

        # Afficher le camembert
        pie_view = QChartView(pie_chart)
        pie_view.setRenderHint(QPainter.Antialiasing)
        chart_layout.addWidget(pie_view)

        # Conteneur pour le tableau
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)

        # Tableau des appareils
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Appareil", "Sessions", "Taux d'arrêt"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Remplir le tableau
        for i, device in enumerate(device_stats):
            table.insertRow(i)
            device_name = device["device"] if device["device"] else "Inconnu"
            count = device["count"]
            terminated = device["terminated_count"]

            # Calculer le taux d'arrêt
            rate_value = (terminated / count) * 100 if count > 0 else 0
            rate_str = f"{rate_value:.1f}%" if count > 0 else "N/A"

            table.setItem(i, 0, QTableWidgetItem(device_name))

            # Stocker Sessions comme valeur numérique pour le tri
            count_item = QTableWidgetItem()
            count_item.setData(Qt.DisplayRole, count)
            table.setItem(i, 1, count_item)

            # Utiliser la classe personnalisée pour le taux d'arrêt
            rate_item = PercentageTableItem(rate_str, rate_value)
            table.setItem(i, 2, rate_item)

        # Activer le tri pour ce tableau
        self.enable_sorting_for_table(table)

        # Configurer le tri initial par la colonne "Taux d'arrêt" (colonne 2) par ordre décroissant
        table.sortItems(2, Qt.DescendingOrder)

        table_layout.addWidget(table)

        # Ajouter les widgets au séparateur
        splitter.addWidget(chart_container)
        splitter.addWidget(table_container)

        # Configurer la taille relative (75% pour le graphique, 25% pour le tableau)
        splitter.setSizes([750, 250])

        # S'assurer que le splitter prend tout l'espace disponible
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(splitter)

        return tab

    def create_geolocation_tab(self, period=None):
        """Créer l'onglet de géolocalisation IP"""
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtCore import QUrl
        import tempfile
        import json
        from data.geoip import GeoIPLocator
        from PyQt5.QtWidgets import QSplitter

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Récupérer les statistiques des IPs en fonction de la période
        if period is None:
            ip_stats = self.db.get_ip_stats()
        elif "days" in period:
            ip_stats = self.db.get_ip_stats(days=period["days"])
        else:
            ip_stats = self.db.get_ip_stats(
                start_date=period["start_date"], end_date=period["end_date"]
            )

        # Récupérer les statistiques des IPs
        ip_stats = self.db.get_ip_stats()

        # Initialiser le localisateur d'IP
        locator = GeoIPLocator()

        # Tableau des informations de localisation
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["Adresse IP", "Pays", "Ville", "Sessions", "Dernier accès"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Données pour la carte
        map_data = {"locations": []}

        # Remplir le tableau
        row = 0
        for ip in ip_stats:
            # Obtenir la localisation
            location = locator.locate_ip(ip["ip_address"])
            if not location:
                continue

            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(ip["ip_address"]))
            table.setItem(row, 1, QTableWidgetItem(location.get("country", "Inconnu")))
            table.setItem(row, 2, QTableWidgetItem(location.get("city", "Inconnu")))

            # Utiliser setData avec Qt.DisplayRole pour stocker le nombre pour le tri
            count_item = QTableWidgetItem()
            count_item.setData(Qt.DisplayRole, ip["count"])
            table.setItem(row, 3, count_item)

            table.setItem(row, 4, QTableWidgetItem(ip["last_seen"]))

            # Ajouter à la carte si des coordonnées existent
            if location.get("latitude") and location.get("longitude"):
                map_data["locations"].append(
                    {
                        "lat": location["latitude"],
                        "lng": location["longitude"],
                        "name": f"{ip['ip_address']} ({ip['count']} sessions)",
                    }
                )

            row += 1

        # Activer le tri pour ce tableau
        self.enable_sorting_for_table(table)

        # Configurer le tri initial par la colonne "Sessions" (colonne 3) par ordre décroissant
        table.sortItems(3, Qt.DescendingOrder)

        layout.addWidget(table)

        # Créer le HTML pour la carte avec Leaflet
        map_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PlexPatrol - Carte des connexions</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <style>
                body, html { 
                    margin: 0; 
                    padding: 0; 
                    height: 100%; 
                    width: 100%;
                    overflow: hidden;
                }
                #map { 
                    position: absolute;
                    top: 0;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 100%; 
                    width: 100%;
                    margin: 0;
                    padding: 0;
                }
                .popup-content {
                    font-family: Arial, sans-serif;
                    padding: 8px;
                    font-size: 14px;
                    text-align: center;
                    background-color: #333;
                    color: white;
                    border-radius: 5px;
                    min-width: 180px;
                }
                .leaflet-popup-content-wrapper {
                    background: #333;
                    color: white;
                    border-radius: 5px;
                    padding: 0;
                }
                .leaflet-popup-tip {
                    background: #333;
                }
                .leaflet-container {
                    background: #1e1e1e; /* Fond de carte adapté au thème sombre */
                }
            </style>
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        </head>
        <body>
            <div id="map"></div>
            <script>
                // Charger les données
                var locationsData = MAP_DATA_PLACEHOLDER;
                
                // Créer la carte avec des options spécifiques
                var map = L.map('map', {
                    worldCopyJump: true,
                    minZoom: 2,
                    maxZoom: 18
                }).setView([46.8, 2.3], 5);
                
                // Ajouter la couche OpenStreetMap
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                    noWrap: true
                }).addTo(map);
                
                // Fonction pour créer le contenu des popups
                function createPopupContent(name) {
                    var parts = name.split('(');
                    var ip = parts[0].trim();
                    var sessions = parts[1].replace(')', '').trim();
                    
                    return '<div class="popup-content">' +
                        '<strong>IP:</strong> ' + ip + '<br>' +
                        '<strong>Sessions:</strong> ' + sessions +
                        '</div>';
                }
                
                // Ajouter les marqueurs
                var markers = [];
                
                if (locationsData.locations && locationsData.locations.length > 0) {
                    var markerGroup = L.featureGroup();
                    
                    for (var i = 0; i < locationsData.locations.length; i++) {
                        var loc = locationsData.locations[i];
                        var marker = L.marker([loc.lat, loc.lng])
                            .bindPopup(createPopupContent(loc.name), {
                                closeButton: false
                            });
                        
                        markerGroup.addLayer(marker);
                        markers.push(marker);
                    }
                    
                    markerGroup.addTo(map);
                    
                    if (locationsData.locations.length === 1) {
                        var loc = locationsData.locations[0];
                        map.setView([loc.lat, loc.lng], 5);
                    } else {
                        map.fitBounds(markerGroup.getBounds(), {
                            padding: [50, 50],
                            maxZoom: 5
                        });
                        
                        setTimeout(function() {
                            var currentZoom = map.getZoom();
                            if (currentZoom > 5) {
                                map.setZoom(5);
                            }
                            if (currentZoom < 4) {
                                map.setZoom(4);
                            }
                        }, 100);
                    }
                    
                    markerGroup.eachLayer(function(layer) {
                        layer.on('mouseover', function(e) {
                            this.openPopup();
                        });
                        layer.on('click', function(e) {
                            if (this.isPopupOpen()) {
                                this.closePopup();
                            } else {
                                this.openPopup();
                            }
                        });
                    });
                }
                
                // Redimensionner la carte lors du chargement et du redimensionnement de la fenêtre
                function resizeMap() {
                    map.invalidateSize();
                }
                
                // S'assurer que la carte est correctement dimensionnée
                setTimeout(resizeMap, 100);
                setTimeout(resizeMap, 500);
                
                // Redimensionner également lors des changements de taille de fenêtre
                window.addEventListener('resize', resizeMap);
            </script>
        </body>
        </html>
        """

        # Remplacer les placeholders
        map_html = map_html.replace("MAP_DATA_PLACEHOLDER", json.dumps(map_data))

        # Écrire dans un fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        with open(temp_file.name, "w", encoding="utf-8") as f:
            f.write(map_html)

            # Créer une disposition spécifique pour la carte qui garantit une hauteur fixe
        web_view = QWebEngineView()
        web_view.setMinimumHeight(400)  # Hauteur minimale fixe pour la carte
        web_view.load(QUrl.fromLocalFile(temp_file.name))

        # Ajouter le tableau et la carte dans un splitter vertical
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(table)
        splitter.addWidget(web_view)

        # Configurer les tailles relatives (50% tableau, 50% carte)
        splitter.setSizes([400, 400])

        layout.addWidget(splitter)

        # Fermer le localisateur
        locator.close()

        return tab
