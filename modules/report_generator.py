# modules/report_generator.py

from datetime import datetime
import os

class ReportGenerator:
    """Génère le rapport HTML des tests"""
    
    def __init__(self, results):
        self.results = results
        
    def generate(self):
        """Génère le rapport HTML"""
        os.makedirs('test_reports', exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = f'test_reports/report_{timestamp}.html'
        
        html = self.build_html()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return report_path
    
    def build_html(self):
        """Construit le contenu HTML"""
        total = self.results['total_tests']
        passed = self.results['passed']
        failed = self.results['failed']
        errors = self.results['errors']
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Tests - P2P Arbitrage</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 14px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }}
        .metric:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .metric-value {{ font-size: 36px; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric.success .metric-value {{ color: #10b981; }}
        .metric.danger .metric-value {{ color: #ef4444; }}
        .metric.warning .metric-value {{ color: #f59e0b; }}
        .metric.info .metric-value {{ color: #3b82f6; }}
        .categories {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        .categories h2 {{ margin-bottom: 20px; color: #1f2937; }}
        .category-row {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #e5e7eb; }}
        .category-row:last-child {{ border-bottom: none; }}
        .category-name {{ font-weight: 600; min-width: 150px; }}
        .category-bar {{ flex: 1; margin: 0 20px; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }}
        .category-bar-fill {{ height: 100%; background: #10b981; transition: width 0.3s; }}
        .category-stats {{ color: #666; font-size: 14px; min-width: 120px; text-align: right; }}
        .failures {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .failures h2 {{ margin-bottom: 20px; color: #ef4444; }}
        .no-failures {{ text-align: center; padding: 40px; color: #10b981; }}
        .no-failures-icon {{ font-size: 48px; margin-bottom: 10px; }}
        .failure-item {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; margin-bottom: 15px; border-radius: 8px; }}
        .failure-item h3 {{ color: #991b1b; margin-bottom: 10px; font-size: 16px; }}
        .failure-meta {{ color: #666; font-size: 12px; margin-bottom: 15px; }}
        .failure-details {{ font-size: 14px; color: #666; line-height: 1.6; }}
        .check-item {{ margin: 8px 0; padding: 10px; background: white; border-radius: 4px; font-size: 13px; }}
        .check-passed {{ border-left: 3px solid #10b981; }}
        .check-failed {{ border-left: 3px solid #ef4444; color: #dc2626; }}
        .error-item {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; margin-bottom: 15px; border-radius: 8px; }}
        .error-item h3 {{ color: #92400e; margin-bottom: 10px; }}
        .error-message {{ background: white; padding: 10px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px; color: #dc2626; white-space: pre-wrap; word-break: break-all; }}
        .footer {{ text-align: center; margin-top: 40px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Rapport de Tests Automatisés</h1>
            <p>Système P2P Arbitrage - Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="metric info">
                <div class="metric-label">Tests Totaux</div>
                <div class="metric-value">{total}</div>
            </div>
            <div class="metric success">
                <div class="metric-label">Réussis</div>
                <div class="metric-value">{passed}</div>
            </div>
            <div class="metric danger">
                <div class="metric-label">Échoués</div>
                <div class="metric-value">{failed}</div>
            </div>
            <div class="metric warning">
                <div class="metric-label">Erreurs</div>
                <div class="metric-value">{errors}</div>
            </div>
        </div>
        
        <div class="summary">
            <div class="metric {'success' if pass_rate >= 80 else 'warning' if pass_rate >= 60 else 'danger'}">
                <div class="metric-label">Taux de Réussite</div>
                <div class="metric-value">{pass_rate:.1f}%</div>
            </div>
        </div>
        
        <div class="categories">
            <h2>Résultats par Catégorie</h2>
            {self.build_categories_section()}
        </div>
        
        <div class="failures">
            <h2>Tests Échoués et Erreurs</h2>
            {self.build_failures_section()}
        </div>
        
        <div class="footer">
            <p>Rapport généré par le système de tests automatisés P2P Arbitrage</p>
            <p>Durée totale: {self.calculate_total_duration()}</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def build_categories_section(self):
        """Construit la section des catégories"""
        html = ""
        
        for cat_name, cat_data in self.results['categories'].items():
            total = cat_data['total']
            passed = cat_data['passed']
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            html += f"""
            <div class="category-row">
                <div class="category-name">{cat_name.upper()}</div>
                <div class="category-bar">
                    <div class="category-bar-fill" style="width: {pass_rate}%"></div>
                </div>
                <div class="category-stats">{passed}/{total} ({pass_rate:.1f}%)</div>
            </div>"""
        
        return html
    
    def build_failures_section(self):
        """Construit la section des échecs"""
        failed_tests = self.results.get('failed_tests', [])
        
        if not failed_tests:
            return """
            <div class="no-failures">
                <div class="no-failures-icon">✓</div>
                <p>Aucun test échoué - Tous les tests sont passés avec succès!</p>
            </div>"""
        
        html = ""
        
        for test in failed_tests:
            if test['status'] == 'ERROR':
                html += self.build_error_item(test)
            else:
                html += self.build_failure_item(test)
        
        return html
    
    def build_failure_item(self, test):
        """Construit un item d'échec"""
        html = f"""
        <div class="failure-item">
            <h3>{test['test_name']}</h3>
            <div class="failure-meta">
                ID: {test['test_id']} | Durée: {test['duration']:.2f}s
            </div>
            <div class="failure-details">
                <strong>Vérifications échouées:</strong>
        """
        
        for check in test.get('failed_checks', []):
            html += f"""
                <div class="check-item check-failed">
                    <strong>{check['name']}</strong><br>
                    Attendu: {check['expected']}<br>
                    Obtenu: {check['actual']}
                </div>"""
        
        # Afficher aussi les vérifications réussies
        passed_checks = [c for c in test.get('all_checks', []) if c['passed']]
        if passed_checks:
            html += "<br><strong>Vérifications réussies:</strong>"
            for check in passed_checks:
                html += f"""
                <div class="check-item check-passed">
                    ✓ {check['name']}
                </div>"""
        
        html += """
            </div>
        </div>"""
        
        return html
    
    def build_error_item(self, test):
        """Construit un item d'erreur"""
        return f"""
        <div class="error-item">
            <h3>{test['test_name']}</h3>
            <div class="failure-meta">
                ID: {test['test_id']} | Durée: {test['duration']:.2f}s
            </div>
            <div class="failure-details">
                <strong>Erreur rencontrée:</strong>
                <div class="error-message">{test.get('error', 'Erreur inconnue')}</div>
            </div>
        </div>"""
    
    def calculate_total_duration(self):
        """Calcule la durée totale d'exécution"""
        start = datetime.fromisoformat(self.results['start_time'])
        end = datetime.now()
        duration = (end - start).total_seconds()
        
        if duration < 60:
            return f"{duration:.1f} secondes"
        elif duration < 3600:
            minutes = duration / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = duration / 3600
            return f"{hours:.1f} heures"