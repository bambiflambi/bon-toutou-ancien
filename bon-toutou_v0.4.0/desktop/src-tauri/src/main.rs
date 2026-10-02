// Bon toutou — app de bureau. Elle lance le moteur embarqué (programme « bontoutou-engine »),
// qui n'écoute que cet ordinateur (127.0.0.1, sur un port libre choisi ici), puis l'affiche dans sa fenêtre.
// Quand l'app se ferme, le moteur s'arrête avec elle. Aucune connexion vers internet ici.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{TcpListener, TcpStream};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct Engine(Mutex<Option<CommandChild>>);

/// Un port libre sur 127.0.0.1 (jamais sur le réseau).
fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|a| a.port())
        .unwrap_or(8765)
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let port = free_port();
            let (_rx, child) = app
                .shell()
                .sidecar("bontoutou-engine")?
                .args(["--port", &port.to_string(), "--app", "--watch-pid", &std::process::id().to_string()])
                .spawn()?;
            app.manage(Engine(Mutex::new(Some(child))));
            let handle = app.handle().clone();
            // On attend que le moteur réponde (premier lancement : jusqu'à ~30 s le temps de se décompresser).
            std::thread::spawn(move || {
                let start = Instant::now();
                while start.elapsed() < Duration::from_secs(60) {
                    if TcpStream::connect(("127.0.0.1", port)).is_ok() {
                        let url = format!("http://127.0.0.1:{}/", port);
                        if let (Some(win), Ok(parsed)) = (handle.get_webview_window("main"), url.parse()) {
                            let _ = win.navigate(parsed);
                        }
                        return;
                    }
                    std::thread::sleep(Duration::from_millis(250));
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Bon toutou n'a pas pu démarrer");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(engine) = handle.try_state::<Engine>() {
                if let Some(child) = engine.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        }
    });
}
