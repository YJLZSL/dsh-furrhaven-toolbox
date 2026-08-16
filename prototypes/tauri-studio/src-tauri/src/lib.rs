use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Serialize)]
struct FhOutput {
    code: i32,
    stdout: String,
    stderr: String,
    combined: String,
}

#[derive(Serialize)]
struct DirEntry {
    name: String,
    path: String,
    is_dir: bool,
    is_file: bool,
}

#[cfg(windows)]
fn hide_console(cmd: &mut Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}

fn finish_output(output: std::process::Output) -> FhOutput {
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    FhOutput {
        code: output.status.code().unwrap_or(-1),
        combined: format!("{stdout}{stderr}"),
        stdout,
        stderr,
    }
}

/// 运行 `fh` CLI；找不到时回退 `python -m furrhaven.cli`。
#[tauri::command]
fn run_fh(cwd: String, args: Vec<String>) -> Result<FhOutput, String> {
    let mut cmd = Command::new("fh");
    cmd.args(&args).current_dir(&cwd);
    #[cfg(windows)]
    hide_console(&mut cmd);

    match cmd.output() {
        Ok(output) => Ok(finish_output(output)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            let mut py = Command::new("python");
            py.arg("-m").arg("furrhaven.cli").args(&args).current_dir(&cwd);
            #[cfg(windows)]
            hide_console(&mut py);
            py.output()
                .map(finish_output)
                .map_err(|e2| format!("fh 与 python -m furrhaven.cli 均不可用：{e2}"))
        }
        Err(e) => Err(format!("运行 fh 失败：{e}")),
    }
}

#[tauri::command]
fn fh_version() -> Result<FhOutput, String> {
    run_fh(
        std::env::current_dir()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string(),
        vec!["--version".into()],
    )
}

#[tauri::command]
fn read_text_file(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|e| format!("读取失败 {path}: {e}"))
}

#[tauri::command]
fn write_text_file(path: String, content: String) -> Result<(), String> {
    let p = Path::new(&path);
    if let Some(parent) = p.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("创建目录失败: {e}"))?;
    }
    fs::write(p, content).map_err(|e| format!("写入失败 {path}: {e}"))
}

#[tauri::command]
fn file_exists(path: String) -> bool {
    Path::new(&path).exists()
}

#[tauri::command]
fn list_dir(path: String) -> Result<Vec<DirEntry>, String> {
    let dir = Path::new(&path);
    if !dir.is_dir() {
        return Err(format!("不是目录：{path}"));
    }
    let mut out: Vec<DirEntry> = Vec::new();
    for entry in fs::read_dir(dir).map_err(|e| format!("读取目录失败: {e}"))? {
        let entry = entry.map_err(|e| format!("读取条目失败: {e}"))?;
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') || name == "node_modules" || name == "target" {
            continue;
        }
        let ft = entry.file_type().map_err(|e| format!("stat 失败: {e}"))?;
        let is_dir = ft.is_dir();
        let is_file = ft.is_file();
        if !is_dir && !is_file {
            continue;
        }
        out.push(DirEntry {
            path: entry.path().to_string_lossy().to_string(),
            name,
            is_dir,
            is_file,
        });
    }
    out.sort_by(|a, b| b.is_dir.cmp(&a.is_dir).then_with(|| a.name.cmp(&b.name)));
    Ok(out)
}

#[tauri::command]
fn project_root(path: String) -> Result<String, String> {
    let mut cur = PathBuf::from(path);
    if cur.is_file() {
        cur.pop();
    }
    loop {
        if cur.join("fh.config.yaml").exists() {
            return Ok(cur.to_string_lossy().to_string());
        }
        if !cur.pop() {
            break;
        }
    }
    Err("该目录不在 fh 项目内（缺 fh.config.yaml）".into())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            run_fh,
            fh_version,
            read_text_file,
            write_text_file,
            file_exists,
            list_dir,
            project_root
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
