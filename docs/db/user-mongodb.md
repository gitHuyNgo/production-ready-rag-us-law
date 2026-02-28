# User MongoDB

**Owner**: user-api  
**Purpose**: Document store for user profiles (display name, bio, and other non-security attributes).

## Usage

- user-api uses MongoDB to persist and retrieve profiles by `user_id` (the JWT `sub` from auth-api).
- No passwords or credentials are stored; only profile fields and the user reference.
- Collection and document shape are defined by the user-api models (e.g. `UserProfile`); typically one document per user keyed by `user_id`.

## Configuration

- Connection and database/collection names are configured via user-api environment (see `app/user-api` config). Default in Docker Compose is a `mongo:7` service on port 27017.
