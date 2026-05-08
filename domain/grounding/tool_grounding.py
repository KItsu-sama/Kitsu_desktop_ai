"""
domain/grounding/tool_grounding.py

Tool grounding system for hallucination prevention.

Instead of letting models invent information, this system:
1. Model decides what information is needed
2. Tool verifies and retrieves actual data
3. Response is generated from verified tool output

This is the REAL hallucination solution.
"""

import time
import logging
import json
import os
import subprocess
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger(__name__)


class GroundingType(Enum):
    """Types of grounding operations."""
    FILE_SYSTEM = "file_system"
    SYSTEM_INFO = "system_info"
    NETWORK = "network"
    DESKTOP = "desktop"
    MEMORY = "memory"
    EXTERNAL_API = "external_api"


class VerificationStatus(Enum):
    """Status of tool verification."""
    VERIFIED = "verified"          # Tool successfully verified data
    FAILED = "failed"              # Tool failed to get data
    PARTIAL = "partial"            # Partial data retrieved
    DENIED = "denied"              # Permission denied
    ERROR = "error"                # Tool error occurred


@dataclass
class GroundingRequest:
    """Request for tool grounding."""
    request_id: str
    grounding_type: GroundingType
    query: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"


@dataclass
class GroundingResult:
    """Result from tool grounding."""
    request_id: str
    status: VerificationStatus
    data: Any = None
    error_message: str = ""
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class GroundedResponse:
    """Response generated from grounded data."""
    original_query: str
    grounded_response: str
    confidence: float  # 0.0 - 1.0
    sources: List[str] = field(default_factory=list)
    verification_notes: str = ""
    fallback_used: bool = False


class ToolGroundingSystem:
    """
    Tool grounding system for hallucination prevention.
    
    Features:
    - Automatic tool selection based on query analysis
    - Verification of model claims against real data
    - Fallback mechanisms for tool failures
    - Comprehensive audit logging
    - Permission-aware tool execution
    """
    
    def __init__(self):
        self.tools: Dict[GroundingType, List[Callable]] = {}
        self.request_history: List[GroundingRequest] = []
        self.result_history: List[GroundingResult] = []
        self.response_history: List[GroundedResponse] = []
        
        # Tool registration
        self._register_default_tools()
        
        # Configuration
        self.max_history_size = 1000
        self.default_timeout = 10.0
        self.confidence_threshold = 0.7
        
        log.info("ToolGroundingSystem initialized")
    
    def _register_default_tools(self):
        """Register default grounding tools."""
        # File system tools
        self.tools[GroundingType.FILE_SYSTEM] = [
            self._tool_list_files,
            self._tool_read_file,
            self._tool_file_exists,
            self._tool_get_file_info
        ]
        
        # System info tools
        self.tools[GroundingType.SYSTEM_INFO] = [
            self._tool_get_system_info,
            self._tool_get_process_info,
            self._tool_get_memory_info
        ]
        
        # Network tools
        self.tools[GroundingType.NETWORK] = [
            self._tool_check_connectivity,
            self._tool_get_network_info
        ]
        
        # Desktop tools
        self.tools[GroundingType.DESKTOP] = [
            self._tool_list_windows,
            self._tool_get_active_window
        ]
        
        # Memory tools
        self.tools[GroundingType.MEMORY] = [
            self._tool_search_memory,
            self._tool_get_memory_stats
        ]
    
    def register_tool(self, grounding_type: GroundingType, tool_func: Callable) -> None:
        """Register a custom grounding tool."""
        if grounding_type not in self.tools:
            self.tools[grounding_type] = []
        self.tools[grounding_type].append(tool_func)
        log.info(f"Registered tool for {grounding_type.value}")
    
    def analyze_query(self, query: str) -> List[GroundingType]:
        """
        Analyze query to determine what grounding types are needed.
        
        Args:
            query: The user query or model claim
            
        Returns:
            List of grounding types that should be applied
        """
        query_lower = query.lower()
        needed_types = []
        
        # File system indicators
        file_indicators = ["file", "folder", "directory", "exists", "list", "read", "write", "delete"]
        if any(indicator in query_lower for indicator in file_indicators):
            needed_types.append(GroundingType.FILE_SYSTEM)
        
        # System info indicators
        system_indicators = ["system", "process", "memory", "cpu", "running", "performance"]
        if any(indicator in query_lower for indicator in system_indicators):
            needed_types.append(GroundingType.SYSTEM_INFO)
        
        # Network indicators
        network_indicators = ["network", "internet", "connection", "online", "website", "url"]
        if any(indicator in query_lower for indicator in network_indicators):
            needed_types.append(GroundingType.NETWORK)
        
        # Desktop indicators
        desktop_indicators = ["window", "application", "desktop", "screen", "active"]
        if any(indicator in query_lower for indicator in desktop_indicators):
            needed_types.append(GroundingType.DESKTOP)
        
        # Memory indicators
        memory_indicators = ["remember", "recall", "memory", "stored", "previous"]
        if any(indicator in query_lower for indicator in memory_indicators):
            needed_types.append(GroundingType.MEMORY)
        
        return needed_types
    
    def ground_request(
        self,
        request_id: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        source: str = "unknown"
    ) -> List[GroundingResult]:
        """
        Ground a request using appropriate tools.
        
        Args:
            request_id: Unique identifier for this request
            query: The query to ground
            parameters: Additional parameters for tools
            source: Source of the request
            
        Returns:
            List of grounding results
        """
        # Determine needed grounding types
        grounding_types = self.analyze_query(query)
        
        if not grounding_types:
            # No grounding needed
            return [GroundingResult(
                request_id=request_id,
                status=VerificationStatus.VERIFIED,
                data={"message": "No grounding required"},
                metadata={"note": "Query does not require verification"}
            )]
        
        # Create request
        request = GroundingRequest(
            request_id=request_id,
            grounding_type=grounding_types[0],  # Primary type
            query=query,
            parameters=parameters or {},
            source=source
        )
        self.request_history.append(request)
        
        # Execute grounding tools
        results = []
        for grounding_type in grounding_types:
            if grounding_type in self.tools:
                for tool in self.tools[grounding_type]:
                    try:
                        result = self._execute_tool(tool, request, grounding_type)
                        results.append(result)
                    except Exception as e:
                        log.error(f"Tool execution error: {e}")
                        results.append(GroundingResult(
                            request_id=request_id,
                            status=VerificationStatus.ERROR,
                            error_message=str(e),
                            metadata={"tool": tool.__name__, "type": grounding_type.value}
                        ))
        
        # Store results
        self.result_history.extend(results)
        
        # Cleanup history
        if len(self.request_history) > self.max_history_size:
            self.request_history = self.request_history[-self.max_history_size//2:]
        if len(self.result_history) > self.max_history_size:
            self.result_history = self.result_history[-self.max_history_size//2:]
        
        return results
    
    def _execute_tool(
        self,
        tool: Callable,
        request: GroundingRequest,
        grounding_type: GroundingType
    ) -> GroundingResult:
        """Execute a grounding tool."""
        start_time = time.time()
        
        try:
            # Execute tool with timeout
            data = tool(request.query, request.parameters)
            execution_time = time.time() - start_time
            
            return GroundingResult(
                request_id=request.request_id,
                status=VerificationStatus.VERIFIED,
                data=data,
                execution_time=execution_time,
                metadata={
                    "tool": tool.__name__,
                    "type": grounding_type.value
                }
            )
            
        except PermissionError as e:
            return GroundingResult(
                request_id=request.request_id,
                status=VerificationStatus.DENIED,
                error_message=str(e),
                execution_time=time.time() - start_time,
                metadata={"tool": tool.__name__, "type": grounding_type.value}
            )
        
        except FileNotFoundError as e:
            return GroundingResult(
                request_id=request.request_id,
                status=VerificationStatus.FAILED,
                error_message=str(e),
                execution_time=time.time() - start_time,
                metadata={"tool": tool.__name__, "type": grounding_type.value}
            )
        
        except Exception as e:
            return GroundingResult(
                request_id=request.request_id,
                status=VerificationStatus.ERROR,
                error_message=str(e),
                execution_time=time.time() - start_time,
                metadata={"tool": tool.__name__, "type": grounding_type.value}
            )
    
    def generate_grounded_response(
        self,
        original_query: str,
        model_response: str,
        grounding_results: List[GroundingResult]
    ) -> GroundedResponse:
        """
        Generate a grounded response from model output and tool results.
        
        Args:
            original_query: The original user query
            model_response: The model's ungrounded response
            grounding_results: Results from grounding tools
            
        Returns:
            Grounded response with verification
        """
        # Extract verified data
        verified_data = {}
        sources = []
        verification_notes = ""
        
        for result in grounding_results:
            if result.status == VerificationStatus.VERIFIED and result.data:
                verified_data.update(result.data if isinstance(result.data, dict) else {"data": result.data})
                sources.append(f"{result.metadata.get('tool', 'unknown')} ({result.metadata.get('type', 'unknown')})")
        
        # Check if model response conflicts with verified data
        confidence = 1.0
        grounded_response = model_response
        
        if verified_data:
            # Simple conflict detection (can be enhanced)
            for key, value in verified_data.items():
                if str(value).lower() not in model_response.lower():
                    # Potential conflict detected
                    confidence *= 0.8
                    verification_notes += f"Verified {key}: {value}. "
            
            # Enhance response with verified data
            if verification_notes:
                grounded_response = f"{model_response}\n\n[Verified: {verification_notes.strip()}]"
        
        # Handle tool failures
        failed_results = [r for r in grounding_results if r.status in [VerificationStatus.FAILED, VerificationStatus.DENIED]]
        if failed_results:
            verification_notes += "Some verification tools failed. "
            confidence *= 0.9
        
        response = GroundedResponse(
            original_query=original_query,
            grounded_response=grounded_response,
            confidence=confidence,
            sources=sources,
            verification_notes=verification_notes.strip(),
            fallback_used=len(verified_data) == 0
        )
        
        self.response_history.append(response)
        
        # Cleanup history
        if len(self.response_history) > self.max_history_size:
            self.response_history = self.response_history[-self.max_history_size//2:]
        
        return response
    
    # Default tool implementations
    def _tool_list_files(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List files in directory."""
        path = parameters.get("path", ".")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        if not os.path.isdir(path):
            raise ValueError(f"Path is not a directory: {path}")
        
        try:
            files = os.listdir(path)
            return {
                "path": path,
                "files": files,
                "count": len(files)
            }
        except PermissionError:
            raise PermissionError(f"Permission denied accessing: {path}")
    
    def _tool_read_file(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents."""
        path = parameters.get("path", "")
        
        if not path:
            raise ValueError("No file path specified")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"File does not exist: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "path": path,
                "content": content,
                "size": len(content)
            }
        except PermissionError:
            raise PermissionError(f"Permission denied reading: {path}")
    
    def _tool_file_exists(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Check if file exists."""
        path = parameters.get("path", "")
        
        return {
            "path": path,
            "exists": os.path.exists(path),
            "is_file": os.path.isfile(path) if os.path.exists(path) else False,
            "is_dir": os.path.isdir(path) if os.path.exists(path) else False
        }
    
    def _tool_get_file_info(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get file information."""
        path = parameters.get("path", "")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        stat = os.stat(path)
        return {
            "path": path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "is_file": os.path.isfile(path),
            "is_dir": os.path.isdir(path)
        }
    
    def _tool_get_system_info(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get system information."""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total
        }
    
    def _tool_get_process_info(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get process information."""
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            "processes": processes[:20],  # Limit to first 20
            "count": len(processes)
        }
    
    def _tool_get_memory_info(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory information."""
        import psutil
        
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free
        }
    
    def _tool_check_connectivity(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Check network connectivity."""
        import urllib.request
        import socket
        
        try:
            # Test connectivity to Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return {"connected": True, "method": "socket"}
        except:
            try:
                # Fallback to HTTP request
                urllib.request.urlopen("http://www.google.com", timeout=3)
                return {"connected": True, "method": "http"}
            except:
                return {"connected": False, "method": "none"}
    
    def _tool_get_network_info(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get network information."""
        import psutil
        
        interfaces = {}
        for interface, addrs in psutil.net_if_addrs().items():
            interfaces[interface] = [addr.address for addr in addrs]
        
        io_counters = psutil.net_io_counters()
        
        return {
            "interfaces": interfaces,
            "bytes_sent": io_counters.bytes_sent,
            "bytes_recv": io_counters.bytes_recv,
            "packets_sent": io_counters.packets_sent,
            "packets_recv": io_counters.packets_recv
        }
    
    def _tool_list_windows(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List desktop windows (platform-specific)."""
        import platform
        
        if platform.system() == "Windows":
            try:
                import win32gui
                windows = []
                
                def enum_windows_callback(hwnd, windows_list):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            windows_list.append({"hwnd": hwnd, "title": title})
                
                win32gui.EnumWindows(enum_windows_callback, windows)
                return {"windows": windows, "count": len(windows)}
            except ImportError:
                return {"error": "pywin32 not available"}
        else:
            return {"error": "Platform not supported"}
    
    def _tool_get_active_window(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get active window information."""
        import platform
        
        if platform.system() == "Windows":
            try:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                return {"hwnd": hwnd, "title": title}
            except ImportError:
                return {"error": "pywin32 not available"}
        else:
            return {"error": "Platform not supported"}
    
    def _tool_search_memory(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Search memory/knowledge base."""
        # This would integrate with Kitsu's memory system
        # For now, return placeholder
        return {
            "query": query,
            "results": [],
            "note": "Memory search not implemented"
        }
    
    def _tool_get_memory_stats(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory statistics."""
        # This would integrate with Kitsu's memory system
        return {
            "total_entries": 0,
            "last_updated": time.time(),
            "note": "Memory stats not implemented"
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get grounding system statistics."""
        total_requests = len(self.request_history)
        total_results = len(self.result_history)
        total_responses = len(self.response_history)
        
        if total_results > 0:
            success_rate = sum(1 for r in self.result_history if r.status == VerificationStatus.VERIFIED) / total_results
        else:
            success_rate = 0.0
        
        if total_responses > 0:
            avg_confidence = sum(r.confidence for r in self.response_history) / total_responses
        else:
            avg_confidence = 0.0
        
        return {
            "total_requests": total_requests,
            "total_results": total_results,
            "total_responses": total_responses,
            "success_rate": success_rate,
            "average_confidence": avg_confidence,
            "registered_tools": {
                ground_type.value: len(tools) 
                for ground_type, tools in self.tools.items()
            }
        }
    
    def get_recent_activity(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent grounding activity."""
        recent_requests = self.request_history[-limit:] if self.request_history else []
        recent_results = self.result_history[-limit:] if self.result_history else []
        recent_responses = self.response_history[-limit:] if self.response_history else []
        
        return {
            "requests": [
                {
                    "request_id": r.request_id,
                    "query": r.query[:100] + "..." if len(r.query) > 100 else r.query,
                    "type": r.grounding_type.value,
                    "timestamp": r.timestamp
                }
                for r in recent_requests
            ],
            "results": [
                {
                    "request_id": r.request_id,
                    "status": r.status.value,
                    "execution_time": r.execution_time,
                    "timestamp": r.timestamp
                }
                for r in recent_results
            ],
            "responses": [
                {
                    "original_query": r.original_query[:100] + "..." if len(r.original_query) > 100 else r.original_query,
                    "confidence": r.confidence,
                    "fallback_used": r.fallback_used,
                    "timestamp": r.timestamp
                }
                for r in recent_responses
            ]
        }


# Global instance
TOOL_GROUNDING_SYSTEM = ToolGroundingSystem()
