from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QHBoxLayout,
)
from PyQt5.QtCore import Qt
from data import load_stats


class StatsWidget(QWidget):
    """Widget pour afficher les statistiques des utilisateurs"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_stats()

    def setup_ui(self):
        """Configurer l'interface utilisateur"""
        layout = QVBoxLayout(self)

        # Tableau des statistiques
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
        self.stats_table.setSortingEnabled(True)

        layout.addWidget(self.stats_table)

        # Boutons d'action
        buttons_layout = QHBoxLayout()

        refresh_btn = QPushButton("Rafraîchir")
        refresh_btn.clicked.connect(self.refresh_stats)
        buttons_layout.addWidget(refresh_btn)

        export_btn = QPushButton("Exporter (CSV)")
        export_btn.clicked.connect(self.export_stats)
        buttons_layout.addWidget(export_btn)

        reset_btn = QPushButton("Réinitialiser")
        reset_btn.clicked.connect(self.reset_stats)
        buttons_layout.addWidget(reset_btn)

        layout.addLayout(buttons_layout)

    def load_stats(self):
        """Charger les statistiques depuis la base de données"""
        self.stats = load_stats()
        self.update_stats_table()

    def update_stats_table(self):
        """Mettre à jour l'affichage du tableau des statistiques"""
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

            self.stats_table.setItem(row, 0, QTableWidgetItem(username))

            kill_count_item = QTableWidgetItem()
            kill_count_item.setData(Qt.DisplayRole, kill_count)
            self.stats_table.setItem(row, 1, kill_count_item)

            self.stats_table.setItem(row, 2, QTableWidgetItem(last_kill))
            self.stats_table.setItem(row, 3, QTableWidgetItem(most_used))
            self.stats_table.setItem(row, 4, QTableWidgetItem(kill_rate))

            row += 1

    def refresh_stats(self):
        """Rafraîchir les statistiques"""
        self.load_stats()

    def export_stats(self):
        """Exporter les statistiques au format CSV"""
        # À implémenter
        pass

    def reset_stats(self):
        """Réinitialiser les statistiques"""
        # À implémenter
        pass
