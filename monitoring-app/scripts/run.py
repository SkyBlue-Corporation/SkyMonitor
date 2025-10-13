from app import create_app, db

app = create_app()

@app.cli.command("init-db")
def init_db():
    """Commande pour initialiser la base de données"""
    with app.app_context():
        db.create_all()
    print("✅ Base de données initialisée!")

@app.cli.command("clear-db")
def clear_db():
    """Commande pour vider la base de données"""
    from app.models import Server
    
    with app.app_context():
        try:
            # Compter le nombre d'entrées avant suppression
            count = Server.query.count()
            
            # Supprimer toutes les entrées
            Server.query.delete()
            db.session.commit()
            
            print(f"✅ Base de données vidée - {count} entrées supprimées")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors du vidage: {e}")

@app.cli.command("scan-now")
def scan_now():
    """Commande pour lancer un scan réseau immédiat"""
    from scanner import network_scanner
    
    with app.app_context():
        try:
            print("🔍 Lancement du scan réseau...")
            devices = network_scanner.scan_network()
            
            # Sauvegarder les résultats dans la base
            from app.models import Server
            from datetime import datetime
            
            # Supprimer les anciennes entrées
            Server.query.delete()
            
            # Ajouter les nouveaux appareils détectés
            for device in devices:
                server = Server(
                    name=device['hostname'],
                    ip_address=device['ip'],
                    status=device['status'],
                    type=device['type'],
                    cpu_usage=0.0,  # À mesurer avec un vrai monitoring
                    memory_usage=0.0,  # À mesurer avec un vrai monitoring
                    last_seen=datetime.utcnow(),
                    response_time=device.get('response_time'),
                    open_ports=str(device.get('open_ports', []))
                )
                db.session.add(server)
            
            db.session.commit()
            print(f"✅ Scan terminé - {len(devices)} appareils détectés et sauvegardés")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors du scan: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)