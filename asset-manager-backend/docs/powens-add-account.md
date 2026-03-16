# Ajouter un compte bancaire via Powens

## Prérequis

Les variables d'environnement suivantes doivent être présentes dans `.env` :
- `POWENS_DOMAIN` — ex: `thbdoux-sandbox.biapi.pro`
- `POWENS_CLIENT_ID`
- `POWENS_USER_TOKEN` — token permanent de l'utilisateur

## Procédure

### 1. Générer un code temporaire

```bash
curl -X GET "https://$POWENS_DOMAIN/2.0/auth/token/code" \
  -H "Authorization: Bearer $POWENS_USER_TOKEN"
```

Réponse :
```json
{ "code": "<code_temporaire>", "expires_in": 1800 }
```

Le code est valide **30 minutes**.

### 2. Ouvrir la webview dans un navigateur

Construire l'URL suivante et l'ouvrir :

```
https://webview.powens.com/connect
  ?domain=<POWENS_DOMAIN>
  &client_id=<POWENS_CLIENT_ID>
  &redirect_uri=https://www.google.com
  &code=<code_temporaire>
```

L'utilisateur sélectionne sa banque, saisit ses identifiants et valide l'authentification forte (SCA).

### 3. Confirmer la connexion

Après validation, le navigateur redirige vers :
```
https://www.google.com?connection_id=<id>
```

Vérifier que la connexion apparaît bien :

```bash
curl -X GET "https://$POWENS_DOMAIN/2.0/users/me/connections?expand=accounts" \
  -H "Authorization: Bearer $POWENS_USER_TOKEN"
```

## Notes

- **Redirect URI** : `https://www.google.com` est configurée dans la console Powens. Pour changer, aller sur [console.budget-insight.com](https://console.budget-insight.com).
- **Re-sync** : Powens synchronise automatiquement les connexions une fois par jour. Pas d'action manuelle nécessaire.
- **Reconnexion (SCA expirée)** : après 90 jours, la banque peut exiger une ré-authentification. L'état de la connexion passera à `SCARequired` — répéter la même procédure avec `/auth/webview/reconnect` à la place de `/connect`.
