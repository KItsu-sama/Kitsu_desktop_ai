---
description: Complete modern first-run setup workflow showing all files, classes, and methods
---

# Modern First-Run Setup Workflow

## 🚀 Entry Points

### 1. CLI Entry Point: `r.py --first-run`
```python
# File: r.py
# Method: parse_args() → main()
# Lines: 103-157, 279-283

if overrides.get("modern_first_run"):
    from src.kitsu.first_run import run_modern_first_run
    success = asyncio.run(run_modern_first_run(interactive=True))
    sys.exit(0 if success else 1)
```

### 2. Direct Entry Point: `src/kitsu/first_run.py --run`
```python
# File: src/kitsu/first_run.py
# Method: main() (CLI handler)
# Lines: 269-287

elif args.run:
    success = asyncio.run(run_modern_first_run())
    sys.exit(0 if success else 1)
```

### 3. Launcher Entry Point: `src/kitsu/launcher.py`
```python
# File: src/kitsu/launcher.py
# Class: ModernLauncher
# Method: start()
# Lines: 70-78

if not check_modern_setup_complete():
    logger.info("First-run setup needed, running modern initialization...")
    from kitsu.first_run import run_modern_first_run
    success = await run_modern_first_run(interactive=True)
    if not success:
        print("\n❌ First-run setup failed. Please check logs.")
        return
```

## 📋 Complete Workflow Flow

### Phase 1: Entry & Detection

#### **Step 1**: Entry Point
```
r.py --first-run
    ↓
parse_args() → overrides["modern_first_run"] = True
    ↓
run_modern_first_run(interactive=True)
```

#### **Step 2**: Modern First-Run Check
```
src/kitsu/first_run.py
    ↓
run_modern_first_run(interactive=True)
    ↓
modern_first_run.run_setup(interactive)
```

#### **Step 3**: Class Initialization
```
Class: ModernFirstRun
File: src/kitsu/first_run.py
Lines: 30-36

def __init__(self):
    self.system_info = None
    self.wizard_results = {}
```

### Phase 2: Setup Execution

#### **Step 4**: Main Setup Method
```
Class: ModernFirstRun
Method: run_setup(interactive=True)
File: src/kitsu/first_run.py
Lines: 37-97

async def run_setup(self, interactive: bool = True) -> bool:
```

#### **Step 5**: System Detection
```
Method: detect_system_info()
File: scripts/first_run.py
Lines: 52-101

def detect_system_info() -> Dict[str, Any]:
    # Platform detection
    info["platform"] = platform.system().lower()
    
    # GPU detection
    import torch
    info["capabilities"]["gpu"] = torch.cuda.is_available()
    
    # Audio detection  
    import pyaudio
    info["capabilities"]["audio_input"] = True
    
    # Headless detection
    if not sys.stdin or not sys.stdin.isatty():
        info["headless"] = True
```

#### **Step 6**: Interactive vs Default Setup
```
# Interactive Path
Method: _run_interactive_wizard()
File: src/kitsu/first_run.py
Lines: 99-115

# Default Path  
Method: _apply_default_wizard()
File: src/kitsu/first_run.py
Lines: 117-160
```

### Phase 3: Configuration Writing

#### **Step 7**: Modern Config Writing
```
Method: _write_modern_configs()
File: src/kitsu/first_run.py
Lines: 162-231

# System Config
write_system_config(system_info)
    ↓
File: scripts/first_run.py
Lines: 137-155

# User Profile  
write_user_profile(wizard_results)
    ↓
File: scripts/first_run.py
Lines: 158-185

# Permissions
write_permissions(wizard_results)
    ↓
File: scripts/first_run.py
Lines: 188-203

# Personality
write_personality_config(wizard_results)
    ↓
File: scripts/first_run.py
Lines: 206-224

# Runtime Config
write_runtime_config(wizard_results)
    ↓
File: scripts/first_run.py
Lines: 227-247

# Feature Manifest
write_feature_manifest(wizard_results)
    ↓
File: scripts/first_run.py
Lines: 250-264
```

#### **Step 8**: Config File Writing Process
```
Method: write_config_file()
File: scripts/first_run.py
Lines: 108-134

def write_config_file(path: Path, data: Dict[str, Any], name: str) -> bool:
    # Atomic write process
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp.replace(path)
```

### Phase 4: Directory & Feature Setup

#### **Step 9**: Directory Creation
```
Method: create_directory_structure()
File: scripts/first_run.py
Lines: 271-297

directories = [
    Path("data/config"),
    Path("data/runtime"), 
    Path("data/memory"),
    Path("data/memory/backups"),
    Path("data/logs"),
    Path("data/logs/sessions"),
    Path("data/learning"),
    Path("data/lora"),
    Path("assets/models"),
    Path("assets/sounds")
]
```

#### **Step 10**: Feature Installation
```
Method: install_features()
File: scripts/first_run.py
Lines: 304-350

# Load feature specs
spec_path = Path("docs/featurespec.json")
specs = json.loads(spec_path.read_text(encoding='utf-8'))

# Install each feature
for feature in specs.get("features", []):
    feature_id = feature.get("id")
    if enabled_features.get(feature_id, False):
        # Create feature directories
        Path(folder).mkdir(parents=True, exist_ok=True)
```

### Phase 5: Completion

#### **Step 11**: Mark Completion
```
Method: _mark_first_run_complete()
File: src/kitsu/first_run.py
Lines: 233-247

def _mark_first_run_complete(self) -> bool:
    FIRST_RUN_FLAG.write_text('modern_complete', encoding='utf-8')
    
    # Also create modern marker
    modern_marker = Path("data/runtime/.modern_first_run")
    modern_marker.write_text('true', encoding='utf-8')
```

#### **Step 12**: Status Check
```
Function: check_modern_setup_complete()
File: src/kitsu/first_run.py
Lines: 264-267

def check_modern_setup_complete() -> bool:
    modern_marker = Path("data/runtime/.modern_first_run")
    return modern_marker.exists()
```

## 📁 Files Created

### Configuration Files
```
data/config/
├── system_config.json      # System capabilities + modern runtime info
├── modern_config.json      # Modern modules + event system  
├── user_profile.json       # User preferences
├── permissions.json        # Security permissions
├── personality.json        # AI personality settings
└── runtime_config.json    # Runtime configuration (shared)
```

### Marker Files
```
data/runtime/
├── .first_run_complete      # Legacy completion marker
└── .modern_first_run        # Modern completion marker
```

### Directory Structure
```
data/
├── config/                  # Configuration files
├── runtime/                 # Runtime data & markers
├── memory/                  # Memory storage
│   └── backups/            # Memory backups
├── logs/                   # Log files
│   └── sessions/           # Session logs
├── learning/               # Learning data
├── lora/                  # LoRA models
assets/
├── models/                # AI models
└── sounds/                # Audio files
```

## 🔄 Error Handling

### Import Fallbacks
```python
# Modern wizard fallback
try:
    from setup_wizard import SetupWizard
except ImportError:
    from scripts.setup_wizard import SetupWizard

# Rich prompt fallback  
try:
    from rich.prompt import Confirm
except ImportError:
    response = input("Reset modern configuration? (y/N): ")
```

### Atomic Write Safety
```python
# Prevents corruption during config writes
temp = path.with_suffix('.tmp')
with open(temp, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
temp.replace(path)  # Atomic operation
```

## 🎯 Key Classes & Methods Summary

### ModernFirstRun Class
- `__init__()`: Initialize setup state
- `run_setup(interactive)`: Main setup orchestration
- `_run_interactive_wizard()`: Interactive setup flow
- `_apply_default_wizard()`: Default configuration
- `_write_modern_configs()`: Write all configuration files
- `_mark_first_run_complete()`: Mark setup completion

### Utility Functions (scripts/first_run.py)
- `detect_system_info()`: System capability detection
- `write_config_file()`: Atomic config file writing
- `create_directory_structure()`: Create required directories
- `install_features()`: Feature installation logic

### Configuration Writers (scripts/first_run.py)
- `write_system_config()`: System configuration
- `write_user_profile()`: User profile settings
- `write_permissions()`: Security permissions
- `write_personality_config()`: AI personality
- `write_runtime_config()`: Runtime settings
- `write_feature_manifest()`: Feature manifest

This workflow ensures a complete, atomic, and error-resistant first-run setup process for the modern Kitsu architecture.
