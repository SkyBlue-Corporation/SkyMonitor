#!/usr/bin/env python3
import os
import sys
import subprocess

def is_venv_active():
    """Vérifie si un environnement virtuel est actif"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def check_and_install_requirements():
    """Vérifie et installe les requirements"""
    try:
        # Essayer d'importer les dépendances
        import flask
        import flask_sqlalchemy
        print("✅ Toutes les dépendances sont installées")
        return True
    except ImportError:
        print("❌ Dépendances manquantes, installation...")
        
        # Vérifier si on est dans un venv
        if not is_venv_active():
            print("\n⚠️  ATTENTION: Aucun environnement virtuel actif!")
            print("📋 Veuillez exécuter ces commandes:")
            print("   source venv/bin/activate")
            print("   pip install -r requirements.txt")
            return False
        
        try:
            # Installer les requirements
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dépendances installées avec succès")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Échec de l'installation: {e}")
            return False

def create_sample_data():
    """Crée des données d'exemple"""
    try:
        from app import create_app, db
        from app.models import Server
        
        app = create_app()
        with app.app_context():
            db.create_all()
            
            # Vérifier si des données existent déjà
            if Server.query.count() == 0:
                # Créer des données d'exemple
                sample_servers = [
                    Server(name='Serveur Web Principal', ip_address='192.168.1.10', status='online', cpu_usage=25.0, memory_usage=60.0, type='server'),
                    Server(name='Base de Données', ip_address='192.168.1.11', status='warning', cpu_usage=85.0, memory_usage=45.0, type='server'),
                    Server(name='PC-Administration', ip_address='192.168.1.50', status='online', cpu_usage=10.0, memory_usage=40.0, type='workstation'),
                    Server(name='Container-App', ip_address='192.168.1.100', status='online', cpu_usage=5.0, memory_usage=20.0, type='container'),
                ]
                
                db.session.add_all(sample_servers)
                db.session.commit()
                print("✅ Données d'exemple créées")
            else:
                print("✅ Base de données déjà initialisée")
                
    except Exception as e:
        print(f"⚠️  Attention lors de la création des données: {e}")

def main():
    """Fonction principale"""
    print("🚀 Démarrage du système de monitoring...")
    print(f"📁 Répertoire: {os.getcwd()}")
    
    # Vérifier l'environnement virtuel
    if not is_venv_active():
        print("\n" + "="*60)
        print("❌ ENVIRONNEMENT VIRTUEL NON ACTIF")
        print("="*60)
        print("\n📋 Pour corriger ce problème, exécutez ces commandes:")
        print("\n1. Créer l'environnement virtuel (une seule fois):")
        print("   python3 -m venv venv")
        print("\n2. Activer l'environnement virtuel:")
        print("   source venv/bin/activate")
        print("\n3. Installer les dépendances:")
        print("   pip install -r requirements.txt")
        print("\n4. Redémarrer ce script:")
        print("   python start.py")
        print("\n" + "="*60)
        return
    
    print(f"✅ Environnement virtuel: {sys.prefix}")
    
    # Vérifier et installer les dépendances
    if not check_and_install_requirements():
        return
    
    # Créer les données d'exemple
    create_sample_data()
    
    # Démarrer Flask
    print("\n🌐 Démarrage du serveur Flask...")
    try:
        from run import app
        print("\n" + "="*50)
        print("✅ APPLICATION PRÊTE!")
        print("="*50)
        print("📊 Accédez à: http://localhost:5000")
        print("🛑 Pour arrêter: Ctrl+C")
        print("="*50)
        
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        print("\n🔧 Dépannage:")
        print("1. Vérifiez que tous les fichiers sont présents")
        print("2. Vérifiez la structure des dossiers")
        print("3. Vérifiez les imports dans les fichiers Python")

if __name__ == '__main__':
    main()