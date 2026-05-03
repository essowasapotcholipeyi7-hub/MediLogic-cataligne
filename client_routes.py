import json
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from models import db, Boutique, Article, Commande
from datetime import datetime

client_bp = Blueprint('client', __name__)

# ==================== ACCUEIL & SELECTION BOUTIQUE ====================

@client_bp.route('/')
def accueil():
    # Rediriger vers la page de connexion boutique
    # Les clients accèdent uniquement via lien direct /boutique/<id>
    return redirect(url_for('boutique.connexion'))

@client_bp.route('/boutique/<int:boutique_id>')
def afficher_boutique(boutique_id):
    boutique = Boutique.query.get_or_404(boutique_id)
    
    if not boutique.active:
        flash('Cette boutique n\'est pas disponible', 'danger')
        return redirect(url_for('client.accueil'))
    
    articles = Article.query.filter_by(boutique_id=boutique_id, archive=False).all()
    
    # Récupérer le panier depuis la session
    panier = session.get('panier', {})
    
    return render_template('client/catalogue.html', 
                         boutique=boutique, 
                         articles=articles,
                         panier=panier)

# ==================== GESTION DU PANIER ====================

@client_bp.route('/ajouter_panier', methods=['POST'])
def ajouter_panier():
    article_id = int(request.form.get('article_id'))
    quantite = int(request.form.get('quantite', 1))
    boutique_id = int(request.form.get('boutique_id'))
    
    # Récupérer l'article
    article = Article.query.get_or_404(article_id)
    
    # Initialiser le panier si inexistant
    if 'panier' not in session:
        session['panier'] = {}
    
    panier = session['panier']
    
    if str(article_id) in panier:
        panier[str(article_id)]['quantite'] += quantite
    else:
        panier[str(article_id)] = {
            'nom': article.nom,
            'prix': article.prix,
            'quantite': quantite,
            'boutique_id': boutique_id
        }
    
    session['panier'] = panier
    session.modified = True
    
    flash(f'{article.nom} ajouté au panier', 'success')
    return redirect(url_for('client.afficher_boutique', boutique_id=boutique_id))

@client_bp.route('/panier')
def voir_panier():
    panier = session.get('panier', {})
    total = sum(item['prix'] * item['quantite'] for item in panier.values())
    
    # Récupérer les infos de la boutique
    boutique_id = None
    for item in panier.values():
        boutique_id = item.get('boutique_id')
        break
    
    boutique = Boutique.query.get(boutique_id) if boutique_id else None
    
    return render_template('client/panier.html', panier=panier, total=total, boutique=boutique)

@client_bp.route('/retirer_panier/<int:article_id>')
def retirer_panier(article_id):
    panier = session.get('panier', {})
    
    if str(article_id) in panier:
        del panier[str(article_id)]
        session['panier'] = panier
        session.modified = True
        flash('Article retiré du panier', 'info')
    
    return redirect(url_for('client.voir_panier'))

@client_bp.route('/vider_panier')
def vider_panier():
    session.pop('panier', None)
    flash('Panier vidé', 'info')
    return redirect(url_for('client.accueil'))

# ==================== VALIDATION COMMANDE & WHATSAPP ====================

@client_bp.route('/valider_commande', methods=['GET', 'POST'])
def valider_commande():
    panier = session.get('panier', {})
    
    if not panier:
        flash('Votre panier est vide', 'warning')
        return redirect(url_for('client.accueil'))
    
    # Récupérer la boutique
    boutique_id = None
    for item in panier.values():
        boutique_id = item.get('boutique_id')
        break
    
    boutique = Boutique.query.get(boutique_id)
    
    if not boutique or not boutique.active:
        flash('Boutique non disponible', 'danger')
        return redirect(url_for('client.accueil'))
    
    if request.method == 'POST':
        client_nom = request.form.get('client_nom')
        client_telephone = request.form.get('client_telephone')
        client_adresse = request.form.get('client_adresse')
        instructions = request.form.get('instructions')
        
        # Calculer le total
        total = sum(item['prix'] * item['quantite'] for item in panier.values())
        
        # Sauvegarder la commande en base de données
        commande = Commande(
            boutique_id=boutique_id,
            client_nom=client_nom,
            client_telephone=client_telephone,
            client_adresse=client_adresse,
            articles_json=list(panier.values()),
            total=total
        )
        
        db.session.add(commande)
        db.session.commit()
        
        # Préparer le message WhatsApp avec photos ET instructions
        message = f"🆕 *NOUVELLE COMMANDE*%0A"
        message += f"━━━━━━━━━━━━━━━━━━%0A"
        message += f"👤 *Client:* {client_nom}%0A"
        message += f"📱 *Tél:* {client_telephone}%0A"
        message += f"📍 *Adresse:* {client_adresse}%0A"
        
        # Ajouter les instructions si présentes
        if instructions and instructions.strip():
            message += f"%0A📝 *Instructions:*%0A"
            message += f"\"{instructions.strip()}\"%0A"
        
        message += f"━━━━━━━━━━━━━━━━━━%0A"
        message += f"📦 *ARTICLES COMMANDÉS:*%0A%0A"
        
        for item in panier.values():
            article = Article.query.filter_by(
                nom=item['nom'], 
                boutique_id=boutique_id
            ).first()
            
            message += f"🔹 *{item['nom']}*%0A"
            message += f"   Quantité: {item['quantite']}%0A"
            message += f"   Prix unitaire: {item['prix']:,.0f} FCFA%0A"
            message += f"   Sous-total: {item['prix'] * item['quantite']:,.0f} FCFA%0A"
            
            if article and article.photos_urls and len(article.photos_urls) > 0:
                photo_url = article.photos_urls[0]
                message += f"   🖼️ *Photo:* {photo_url}%0A"
            
            message += f"%0A"
        
        message += f"━━━━━━━━━━━━━━━━━━%0A"
        message += f"💰 *TOTAL: {total:,.0f} FCFA*%0A"
        message += f"━━━━━━━━━━━━━━━━━━%0A"
        message += f"✅ Merci pour votre commande !%0A"
        message += f"📞 Nous vous contacterons sous peu."
        
        numero_whatsapp = boutique.whatsapp.replace(' ', '').replace('+', '') if boutique.whatsapp else ''
        whatsapp_url = f"https://wa.me/{numero_whatsapp}?text={message}"
        
        session.pop('panier', None)
        
        flash('Commande validée avec succès !', 'success')
        return render_template('client/confirmation.html', whatsapp_url=whatsapp_url, commande=commande)
    
    total = sum(item['prix'] * item['quantite'] for item in panier.values())
    
    return render_template('client/commande.html', panier=panier, total=total, boutique=boutique)