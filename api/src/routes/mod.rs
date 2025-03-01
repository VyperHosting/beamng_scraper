use std::{env, sync::Arc};

use axum::{routing::get, Router};
use sqlx::MySqlPool;

mod index;

struct AppState {
    pub db: MySqlPool,
}

impl AppState {
    pub async fn new() -> Self {
        let db = MySqlPool::connect(&env::var("DATABASE_URL").unwrap())
            .await
            .unwrap();

        Self { db }
    }
}

pub async fn router() -> Router {
    let state = Arc::new(AppState::new().await);

    return Router::new()
        .route("/api/v1/mods", get(index::get))
        .with_state(state);
}
