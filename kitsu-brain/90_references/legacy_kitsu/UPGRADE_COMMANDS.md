# Kitsu Architecture Upgrade Commands

## Quick Start Commands

### 1. Upgrade Architecture
Run the full upgrade workflow to install all new features:

```bash
/upgrade
```

### 2. Add New Feature
Add a new component to the architecture:

```bash
/add-feature
```

### 3. Test Installation
Verify all components are working:

```bash
cd "d:\Du lieu o C\Kitsu" && python -c "
import sys
sys.path.append('.')
try:
    from core.compression.binary_nn import BinaryNN, ContextProjectionLayer, BinaryFeatureEmbedding
    from llm.candidate_generator import CandidateGenerator
    from core.memory.vector_memory import VectorMemory
    from core.compression.context_aware_encoder import ContextAwareEncoder
    print('🎉 All new components imported successfully!')
except ImportError as e:
    print(f'❌ Import error: {e}')
"
```

## What These Commands Do

### /upgrade
- Installs binary feature embedding (32-dim vectors)
- Sets up multi-candidate generation (4 responses + ranking)
- Configures vector memory with similarity retrieval
- Adds context projection for large vocabularies
- Implements Markov + Huffman interaction
- Fixes function signatures

### /add-feature
- Provides templates for new components
- Shows integration points in the pipeline
- Includes testing patterns
- Documents common implementation patterns

## Manual Installation

If commands don't work, run these steps manually:

1. **Test BinaryNN with embeddings**:
```bash
cd "d:\Du lieu o C\Kitsu" && python -c "
from core.compression.binary_nn import BinaryNN
import numpy as np
nn = BinaryNN(use_context_projection=True)
print('✅ BinaryNN with embeddings working')
"
```

2. **Test Vector Memory**:
```bash
cd "d:\Du lieu o C\Kitsu" && python -c "
from core.memory.vector_memory import VectorMemory
import numpy as np
memory = VectorMemory()
print('✅ VectorMemory working')
"
```

3. **Test Candidate Generator**:
```bash
cd "d:\Du lieu o C\Kitsu" && python -c "
from llm.candidate_generator import CandidateGenerator
from core.brain.binary_reasoner import BinaryReasoner
reasoner = BinaryReasoner()
print('✅ CandidateGenerator working')
"
```

## Architecture Overview

After upgrade, you'll have:

- **🧠 Enhanced Neural Networks**: Binary features become learnable 32-dim vectors
- **🤖 Smart Response Generation**: 4 candidates ranked by binary reasoning
- **💾 Vector Memory**: Persistent storage with similarity search
- **⚡ Efficient Context**: Large vocabularies compressed to 128-dim
- **🎯 Context-Aware Coding**: Huffman + Markov probability fusion

## Next Steps

1. Run `/upgrade` to install all features
2. Test with your existing Kitsu setup
3. Use `/add-feature` to extend functionality
4. Check `docs/ARCHITECTURE_IMPROVEMENTS.md` for detailed usage

## Support

If you encounter issues:
1. Check that all new files are in correct directories
2. Verify Python path includes Kitsu root
3. Run the manual installation steps above
4. Check the workflow files in `.windsurf/workflows/`
