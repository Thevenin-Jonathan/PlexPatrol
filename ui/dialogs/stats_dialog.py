from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QWidget,
)
from PyQt5.QtChart import (
    QChart,
    QChartView,
    QPieSeries,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt

from utils.constants import UIMessages


class StatisticsDialog(QDialog):
    """Dialogue d'affichage des statistiques détaillées"""

    def __init__(self, stats, parent=None):
        super().__init__(parent)
        self.stats = stats
        self.setWindowTitle("Statistiques détaillées")
        self.setMinimumSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        """Configurer l'interface utilisateur"""
        layout = QVBoxLayout(self)

        # Créer les onglets pour les différents types de statistiques
        tabs = QTabWidget()

        # Onglet 1: Tableau de données
        data_tab = self.create_data_tab()
        tabs.addTab(data_tab, UIMessages.TAB_DATA)

        # Onglet 2: Graphiques
        chart_tab = self.create_chart_tab()
        tabs.addTab(chart_tab, UIMessages.TAB_CHARTS)

        # Onglet 3: Analyse par plateforme
        platform_tab = self.create_platform_tab()
        tabs.addTab(platform_tab, UIMessages.TAB_PLATFORMS)

        layout.addWidget(tabs)

        # Bouton de fermeture
        close_button = QPushButton(UIMessages.BTN_CLOSE)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)

    def create_data_tab(self):
        """Créer l'onglet avec le tableau de données"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

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
            kill_rate = (
                f"{(kill_count / total_sessions) * 100:.1f}%"
                if total_sessions > 0
                else "N/A"
            )

            table.setItem(row, 0, QTableWidgetItem(username))
            table.setItem(row, 1, QTableWidgetItem(str(total_sessions)))
            table.setItem(row, 2, QTableWidgetItem(str(kill_count)))
            table.setItem(row, 3, QTableWidgetItem(last_seen))
            table.setItem(row, 4, QTableWidgetItem(kill_rate))

            row += 1

        layout.addWidget(table)

        return tab

    def create_chart_tab(self):
        """Créer l'onglet avec les graphiques"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Créer un graphique en camembert pour la répartition des arrêts
        pie_chart = QChart()
        pie_chart.setTitle(UIMessages.CHART_SESSIONS_TITLE)
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

    def create_platform_tab(self):
        """Créer l'onglet d'analyse par plateforme"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Créer un graphique en barres pour les plateformes
        bar_chart = QChart()
        bar_chart.setTitle(UIMessages.CHART_PLATFORMS_TITLE)
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
            table.setItem(row, 1, QTableWidgetItem(str(count)))
            row += 1

        layout.addWidget(table)

        return tab
