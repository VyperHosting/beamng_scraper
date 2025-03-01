use std::sync::Arc;

use axum::{extract::{Query, State}, Json};
use serde::Deserialize;
use serde_json::{json, Value};
use phpify::array::array_unshift;

use super::AppState;

#[derive(Deserialize)]
pub struct Pagination {
    page: i64,
    //filter: u8,
}

pub async fn get(State(state): State<Arc<AppState>>, pagination: Query<Pagination>) -> Json<Value> {
    let pagination: Pagination = pagination.0;
    let limit: i64 = 50;
    let offset: i64 = (pagination.page * limit) - limit;
    //let filters = vec!["title", "downloads", "reviews", "rating"];

    /*if !(filters.iter().any(|e| pagination.filter.to_string() == e.to_string())) {
        return Json(json!({
            "error": {
                "message": "Unknown filter provided"
            }
        }));
    }*/

    let mut queue = vec![];
    let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM mods")
        .fetch_one(&state.db)
        .await
        .unwrap();
    
    let data = sqlx::query!("SELECT * FROM mods ORDER BY `downloads` DESC LIMIT ? OFFSET ?", limit, offset)
        .fetch_all(&state.db)
        .await
        .unwrap();

    for val in data.iter().rev() {
        let value: Value = serde_json::json!({
            "id": val.id,
            "title": val.title,
            "icon": val.icon,
            "author": val.author,
            "author_link": val.author_link,
            "description": val.description,
            "tags": val.tags,
            "mod_link": val.mod_link,
            "download_link": val.download_link,
            "rating": val.rating,
            "reviews": val.reviews,
            "downloads": val.downloads,
            "last_updated": val.last_updated
        });

        array_unshift(&mut queue, value);
    }

    Json(json!({
        "pagination": {
            "limit": limit,
            "total_rows": count,
            "pages": ((count as f32) / (limit as f32)).ceil() as isize
        },
        "mods": queue
    }))
}