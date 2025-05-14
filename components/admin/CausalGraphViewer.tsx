'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  Panel,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  ReactFlowInstance,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface ICausalGraphData {
  agent_id: string;
  nodes: { [nodeId: string]: INode };
  edges: { [edgeId: string]: IEdge };
  qa_history: { [qaId: string]: IQA };
}

interface INode {
  id: string;
  label: string;
  is_stance: boolean;
  confidence: number;
  source_qa: string[];
  incoming_edges: string[];
  outgoing_edges: string[];
  status?: 'candidate' | 'anchor';
}

interface IEvidence {
  qa_id: string;
  confidence: number;
}

interface IEdge {
  source: string;
  target: string;
  aggregate_confidence: number;
  evidence: IEvidence[];
  modifier: number;
}

interface IExtractedPair {
  source: string;
  target: string;
  confidence: number;
}

interface IQA {
  question: string;
  answer: string;
  extracted_pairs: IExtractedPair[];
}

interface ICausalGraph {
  _id: string;
  sessionId: string;
  prolificId: string;
  qaPairId: string;
  graphData: ICausalGraphData;
  timestamp: string;
}

// Custom node types
const nodeTypes = {
  stanceNode: ({ data }: { data: any }) => (
    <div className="px-4 py-2 shadow-md rounded-md bg-amber-50 border border-amber-200">
      <div className="font-bold text-xs text-amber-700">Stance Node</div>
      <div className="font-bold text-[#333333]">{data.label}</div>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-amber-500" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-amber-500" />
    </div>
  ),
  beliefNode: ({ data }: { data: any }) => (
    <div className="px-4 py-2 shadow-md rounded-md bg-blue-50 border border-blue-200">
      <div className="font-bold text-xs text-blue-700">Belief Node</div>
      <div className="font-bold text-[#333333]">{data.label}</div>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-blue-500" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-blue-500" />
    </div>
  ),
  candidateNode: ({ data }: { data: any }) => (
    <div className="px-4 py-2 shadow-md rounded-md bg-gray-100 border border-gray-200">
      <div className="font-bold text-xs text-gray-500">Candidate Node</div>
      <div className="font-bold text-gray-600">{data.label}</div>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-gray-400" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-gray-400" />
    </div>
  ),
};

interface CausalGraphViewerProps {
  sessionId: string;
  qaPairId?: string;
  className?: string;
}

export default function CausalGraphViewer({ sessionId, qaPairId, className }: CausalGraphViewerProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [causalGraphs, setCausalGraphs] = useState<ICausalGraph[]>([]);
  const [currentGraphIndex, setCurrentGraphIndex] = useState(0);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [qaInfo, setQaInfo] = useState<{ question: string; answer: string } | null>(null);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  const fetchCausalGraphs = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Build query URL
      let url = `/api/causal-graphs?sessionId=${sessionId}`;
      if (qaPairId) {
        url += `&qaPairId=${qaPairId}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch causal graphs: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Unknown error');
      }
      
      // Sort by timestamp to maintain chronological order
      const sortedGraphs = [...data.causalGraphs].sort((a, b) => {
        // Parse timestamps into Date objects for comparison
        const timeA = new Date(a.timestamp).getTime();
        const timeB = new Date(b.timestamp).getTime();
        return timeA - timeB;  // Oldest first
      });
      
      setCausalGraphs(sortedGraphs);
      
      if (sortedGraphs.length > 0) {
        transformGraphToReactFlow(sortedGraphs[0]);
      } else {
        // Instead of setting an error, set a "no data" state
        setNodes([]);
        setEdges([]);
        setQaInfo(null);
      }
    } catch (err: any) {
      console.error('Error fetching causal graphs:', err);
      // Set a more user-friendly error message
      setError('No causal graph data is available for this session. This may be a new or reset session.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, qaPairId]);

  useEffect(() => {
    fetchCausalGraphs();
  }, [fetchCausalGraphs]);

  const transformGraphToReactFlow = useCallback((graph: ICausalGraph) => {
    if (!graph || !graph.graphData) {
      setNodes([]);
      setEdges([]);
      setQaInfo(null);
      return;
    }

    const graphData = graph.graphData;
    const transformedNodes: Node[] = [];
    const transformedEdges: Edge[] = [];
    
    // Get QA info for the current graph
    let currentQA = null;
    if (graphData.qa_history && Object.keys(graphData.qa_history).length > 0) {
      // Try to find QA with matching ID to the graph's qaPairId
      const qaId = `qa_${graph.qaPairId}`;
      if (graphData.qa_history[qaId]) {
        currentQA = graphData.qa_history[qaId];
      } else {
        // Otherwise take the most recent QA
        const qaIds = Object.keys(graphData.qa_history);
        currentQA = graphData.qa_history[qaIds[qaIds.length - 1]];
      }
    }
    
    if (currentQA) {
      setQaInfo({
        question: currentQA.question,
        answer: currentQA.answer
      });
    } else {
      setQaInfo(null);
    }

    // Transform nodes
    // Analyze graph structure to improve layout
    const nodeIds = graphData.nodes ? Object.keys(graphData.nodes) : [];
    const rootNodes = nodeIds.filter(id => 
      graphData.nodes && graphData.nodes[id] && 
      graphData.nodes[id].incoming_edges && 
      graphData.nodes[id].incoming_edges.length === 0
    );
    const leafNodes = nodeIds.filter(id => 
      graphData.nodes && graphData.nodes[id] && 
      graphData.nodes[id].outgoing_edges && 
      graphData.nodes[id].outgoing_edges.length === 0
    );
    const middleNodes = nodeIds.filter(id => 
      !rootNodes.includes(id) && !leafNodes.includes(id)
    );
    
    // Sort nodes by their position in the causal chain
    const sortedNodes = [...rootNodes, ...middleNodes, ...leafNodes];
    
    // Create a better layout based on graph structure
    if (graphData.nodes) {
      // Improved layout configuration
      const HORIZONTAL_SPACING = 300;  // Further increased spacing between nodes horizontally
      const VERTICAL_SPACING = 200;    // Further increased spacing between levels
      const NODES_PER_ROW = Math.max(3, Math.ceil(Math.sqrt(nodeIds.length * 0.8)));  // Reduce nodes per row to prevent overlap
      
      // Calculate optimal distribution of nodes in each layer
      const rootNodesCount = rootNodes.length;
      const middleNodesCount = middleNodes.length;
      const leafNodesCount = leafNodes.length;
      
      // Get max count to determine optimal width
      const maxNodesInLayer = Math.max(rootNodesCount, middleNodesCount, leafNodesCount, 1);
      
      sortedNodes.forEach((nodeId, index) => {
        const node = graphData.nodes[nodeId];
        if (!node) return; // Skip if node doesn't exist
        
        // Determine node type based on status and is_stance flag
        let nodeType = 'beliefNode';
        if (node.is_stance) {
          nodeType = 'stanceNode';
        } else if (node.status === 'candidate') {
          nodeType = 'candidateNode';
        }

        // Calculate position based on the node's layer and relative position within that layer
        let xPos = 0;
        let yPos = 0;
        
        if (rootNodes.includes(nodeId)) {
          // Calculate position in the top row (root nodes)
          const positionInLayer = rootNodes.indexOf(nodeId);
          xPos = (positionInLayer - (rootNodesCount - 1) / 2) * HORIZONTAL_SPACING;
          yPos = 0;
        } else if (leafNodes.includes(nodeId)) {
          // Calculate position in the bottom row (leaf nodes)
          const positionInLayer = leafNodes.indexOf(nodeId);
          xPos = (positionInLayer - (leafNodesCount - 1) / 2) * HORIZONTAL_SPACING;
          yPos = VERTICAL_SPACING * 2;
        } else {
          // Calculate position in the middle row
          const positionInLayer = middleNodes.indexOf(nodeId);
          
          // If we have many middle nodes, distribute them in a grid
          if (middleNodesCount > NODES_PER_ROW) {
            const row = Math.floor(positionInLayer / NODES_PER_ROW);
            const col = positionInLayer % NODES_PER_ROW;
            xPos = (col - (NODES_PER_ROW - 1) / 2) * HORIZONTAL_SPACING;
            yPos = VERTICAL_SPACING + row * (VERTICAL_SPACING * 0.6);
          } else {
            // Otherwise center them in one row
            xPos = (positionInLayer - (middleNodesCount - 1) / 2) * HORIZONTAL_SPACING;
            yPos = VERTICAL_SPACING;
          }
        }
        
        transformedNodes.push({
          id: nodeId, // Use nodeId as the id to ensure it matches edge connections
          type: nodeType,
          data: {
            label: node.label,
            confidence: node.confidence,
            is_stance: node.is_stance,
            status: node.status || 'anchor'  // Default to anchor if not specified
          },
          position: { 
            x: xPos + Math.random() * 20 - 10,
            y: yPos + Math.random() * 20 - 10
          }
        });
      });
    }

    // Transform edges
    if (graphData.edges) {
      Object.entries(graphData.edges).forEach(([edgeId, edge]) => {
        if (!edge) return; // Skip if edge doesn't exist
        
        // Determine edge style based on confidence and modifier
        let style = {};
        let label = '';
        
        // Add confidence to label
        label = `${Math.round(edge.aggregate_confidence * 100)}%`;
        
        // Style based on modifier (positive = solid, negative = dashed)
        if (edge.modifier < 0) {
          label = `${label} (-)`;
          style = { strokeDasharray: '5,5', stroke: '#a87c7c' }; // Negative influence
        } else {
          label = `${label} (+)`;
          style = { stroke: '#8a936a' }; // Positive influence
        }
        
        // Width based on confidence
        const strokeWidth = 1 + edge.aggregate_confidence * 2;
        style = { ...style, strokeWidth };
        
        transformedEdges.push({
          id: edgeId,
          source: edge.source,
          target: edge.target,
          label,
          labelStyle: { fill: '#5c5c5c', fontWeight: 500, fontSize: 12 },
          style,
          animated: false, // Disable animation
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 15,
            height: 15,
            color: edge.modifier < 0 ? '#a87c7c' : '#8a936a',
          }
        });
      });
    }

    setNodes(transformedNodes);
    setEdges(transformedEdges);
  }, [setNodes, setEdges]);

  const handleGraphChange = useCallback((index: number) => {
    if (index >= 0 && index < causalGraphs.length) {
      setCurrentGraphIndex(index);
      transformGraphToReactFlow(causalGraphs[index]);
      
      // Wait for the graph to be rendered before fitting the view
      setTimeout(() => {
        if (reactFlowInstance.current) {
          reactFlowInstance.current.fitView({
            padding: 0.25,
            minZoom: 0.5,
            maxZoom: 1.5,
            duration: 0 // No animation
          });
        }
      }, 50);
    }
  }, [causalGraphs, transformGraphToReactFlow]);

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <Loader2 className="w-8 h-8 animate-spin text-[#a89f88]" />
        <span className="ml-2 text-[#5c5c5c]">Loading causal graphs...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className={`${className}`}>
        <AlertDescription className="text-gray-600">{error}</AlertDescription>
      </Alert>
    );
  }

  if (causalGraphs.length === 0) {
    return (
      <div className={`text-center p-8 ${className}`}>
        <p className="text-[#8a7f6c]">No causal graphs available for this session yet. The graph will appear after the user answers some questions.</p>
      </div>
    );
  }

  return (
    <div className={`${className} flex flex-col h-full`}>
      {/* Graph navigation */}
      <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-md">
        <div className="text-sm font-medium text-[#5c5c5c]">
          <span>Graph {currentGraphIndex + 1} of {causalGraphs.length}</span>
          <Badge variant="outline" className="ml-2 bg-white text-[#8a7f6c] border-[#d7d2c5]">
            QA Pair: {causalGraphs[currentGraphIndex].qaPairId}
          </Badge>
          <Badge variant="outline" className="ml-2 bg-white text-[#6c788a] border-[#d5d9e0]">
            {new Date(causalGraphs[currentGraphIndex].timestamp).toLocaleString()}
          </Badge>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleGraphChange(currentGraphIndex - 1)}
            disabled={currentGraphIndex === 0}
            className="border-[#d7d2c5] bg-white hover:bg-[#ede9e0] text-[#5c5c5c]"
          >
            ← Earlier
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleGraphChange(currentGraphIndex + 1)}
            disabled={currentGraphIndex === causalGraphs.length - 1}
            className="border-[#d7d2c5] bg-white hover:bg-[#ede9e0] text-[#5c5c5c]"
          >
            Later →
          </Button>
        </div>
      </div>

      {/* QA pair info */}
      {qaInfo && (
        <Card className="mb-4 shadow-sm overflow-hidden">
          <CardHeader className="bg-blue-50 py-3 border-b border-[#e0ddd5]">
            <CardTitle className="text-lg flex items-center">
              <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">
                Q
              </span>
              Question #{currentGraphIndex + 1}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 bg-white">
            <p className="mb-4">{qaInfo.question}</p>
            <div className="mt-4">
              <div className="flex items-center mb-2">
                <span className="bg-green-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">
                  A
                </span>
                <h4 className="font-medium">Answer:</h4>
              </div>
              <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
                {qaInfo.answer || <span className="text-gray-400">(No answer)</span>}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Graph visualization */}
      <div className="flex-grow rounded-md overflow-hidden bg-white" style={{ height: 500 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{
            padding: 0.25,  // Add more padding around nodes (25% of viewport)
            minZoom: 0.5,   // Allow zooming out further if needed
            maxZoom: 1.5,   // Limit maximum zoom
            duration: 0     // No animation
          }}
          defaultEdgeOptions={{
            style: { stroke: '#8f8574' },
            animated: false, // Disable edge animation
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#8f8574',
              width: 15,
              height: 15
            }
          }}
          onInit={(instance) => {
            reactFlowInstance.current = instance;
          }}
        >
          <Controls className="border border-[#e0ddd5] bg-white rounded-md" />
          <Background gap={16} color="#e0ddd5" />
          <Panel position="top-right">
            <div className="bg-white p-3 rounded-md shadow-sm border border-[#e0ddd5]">
              <h4 className="text-xs font-semibold mb-2 text-[#5c5c5c]">Node Types</h4>
              <div className="flex items-center mb-2">
                <div className="w-3 h-3 bg-blue-500 mr-2 rounded-sm"></div>
                <span className="text-xs text-[#5c5c5c]">Belief Node (Anchor)</span>
              </div>
              <div className="flex items-center mb-2">
                <div className="w-3 h-3 bg-gray-400 mr-2 rounded-sm"></div>
                <span className="text-xs text-[#5c5c5c]">Candidate Node</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-amber-500 mr-2 rounded-sm"></div>
                <span className="text-xs text-[#5c5c5c]">Stance Node</span>
              </div>
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
} 