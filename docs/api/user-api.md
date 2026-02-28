# User API

The User API manages non-security user profile data (display name, bio, etc.). It is exposed via the gateway at `/profiles/*`. All profile endpoints require a valid JWT from the Auth API.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/profiles/me` | Bearer | Returns the current user’s profile (user_id, display_name, bio, etc.). |
| PUT | `/profiles/me` | Bearer | Upserts the current user’s profile. Request body: profile fields (e.g. display_name, bio). `user_id` in body is ignored; taken from JWT `sub`. |

## Authentication

- Each request must include `Authorization: Bearer <access_token>` where the token was issued by the Auth API.
- User API verifies the token using the same RS256 **public key** as the gateway. No call to auth-api is made per request.
- The resolved `sub` (user id) is used as the profile primary key in MongoDB.

## Data Store

- **MongoDB**: Profiles are stored as documents keyed by `user_id`. The service does not store passwords or credentials; it only stores profile fields and a reference to the user (user_id from auth).
