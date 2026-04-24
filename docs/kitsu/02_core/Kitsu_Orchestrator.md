Orchestrator → routes → [[EventBus]]
EventBus → connects → [[Modules]]
Modules → include → [[Quiz System]], [[Emotion Engine]]
# Role  
Routes events, selects execution path, handles fallback  
  
# Does NOT do  
- emotion logic  
- quiz logic  
- UI  
  
# Rules  
- event-driven  
- async  
- minimal
# Issue: Orchestrator too complex  
  
Cause:  
- too many responsibilities  
  
Fix:  
- move quiz system to module  
  
Rule learned:  
- orchestrator = routing only

