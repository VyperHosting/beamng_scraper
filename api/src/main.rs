use tokio::net::TcpListener;
mod routes;

#[tokio::main]
async fn main() {
    dotenvy::dotenv().unwrap();
    let router = routes::router().await;
    let listener = TcpListener::bind("0.0.0.0:3000").await.unwrap();

    axum::serve(listener, router).await.unwrap();
}
