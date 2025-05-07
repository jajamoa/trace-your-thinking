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
  ReactFlowInstance
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
  qas: IQA[];
}

interface INodeAppearance {
  qa_ids: string[];
  frequency: number;
}

interface INode {
  id: string;
  label: string;
  type: string;
  range?: number[];
  values?: boolean[];
  semantic_role: string;
  appearance: INodeAppearance;
  incoming_edges: string[];
  outgoing_edges: string[];
}

interface IEdgeFunction {
  target: string;
  inputs: string[];
  function_type: string;
  parameters: {
    weights?: number[];
    bias?: number;
    threshold?: number;
    direction?: string;
  };
  noise_std: number;
  support_qas: string[];
  confidence?: number;
}

interface IEdge {
  from: string;
  to: string;
  function: IEdgeFunction;
  support_qas: string[];
}

interface IBeliefStructure {
  from: string;
  to: string;
  direction: string;
}

interface IBeliefStrength {
  estimated_probability: number;
  confidence_rating: number;
}

interface IParsedBelief {
  belief_structure: IBeliefStructure;
  belief_strength: IBeliefStrength;
  counterfactual?: string;
}

interface IQA {
  qa_id: string;
  question: string;
  answer: string;
  parsed_belief: IParsedBelief;
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
  externalState: ({ data }: { data: any }) => (
    <div className="px-4 py-2 shadow-md rounded-md bg-blue-50 border border-blue-200">
      <div className="font-bold text-xs text-blue-700">{data.semantic_role}</div>
      <div className="font-bold text-[#333333]">{data.label}</div>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-blue-500" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-blue-500" />
    </div>
  ),
  internalAffect: ({ data }: { data: any }) => (
    <div className="px-4 py-2 shadow-md rounded-md bg-purple-50 border border-purple-200">
      <div className="font-bold text-xs text-purple-700">{data.semantic_role}</div>
      <div className="font-bold text-[#333333]">{data.label}</div>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-purple-500" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-purple-500" />
    </div>
  ),
  behavioralIntention: ({ data }: { data: any }) => (
    <div className="px-4 py-2 shadow-md rounded-md bg-amber-50 border border-amber-200">
      <div className="font-bold text-xs text-amber-700">{data.semantic_role}</div>
      <div className="font-bold text-[#333333]">{data.label}</div>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-amber-500" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-amber-500" />
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
        setError('No causal graphs found for this session');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch causal graphs');
      console.error('Error fetching causal graphs:', err);
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
    const qa = graphData.qas && graphData.qas.length > 0 
      ? (graphData.qas.find(qa => qa.qa_id === `qa_${graph.qaPairId}`) || 
         graphData.qas.find(qa => qa.qa_id === graph.qaPairId))
      : null;
    
    if (qa) {
      setQaInfo({
        question: qa.question,
        answer: qa.answer
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
        
        let nodeType = 'default';
        
        // Map semantic role to node type
        switch (node.semantic_role) {
          case 'external_state':
            nodeType = 'externalState';
            break;
          case 'internal_affect':
            nodeType = 'internalAffect';
            break;
          case 'behavioral_intention':
            nodeType = 'behavioralIntention';
            break;
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
          id: node.id,
          type: nodeType,
          data: {
            label: node.label,
            type: node.type,
            values: node.values,
            range: node.range,
            semantic_role: node.semantic_role
          },
          position: { 
            x: xPos + Math.random() * 20 - 10,
            y: yPos + Math.random() * 20 - 10
          }
        });
      });
    }

    // Transform edges - Add null check before using Object.entries
    if (graphData.edges) {
      Object.entries(graphData.edges).forEach(([edgeId, edge]) => {
        if (!edge || !edge.function) return; // Skip if edge or function doesn't exist
        
        const edgeFunction = edge.function;
        
        // Determine edge style based on function type and parameters
        let style = {};
        let label = '';
        
        if (edgeFunction.function_type === 'sigmoid') {
          // Label with weight and bias
          const weight = edgeFunction.parameters?.weights?.[0] || 0;
          const bias = edgeFunction.parameters?.bias || 0;
          label = `W: ${weight.toFixed(1)}, B: ${bias.toFixed(1)}`;
          
          // Style based on weight (positive = solid, negative = dashed)
          if (weight < 0) {
            style = { strokeDasharray: '5,5', stroke: '#a87c7c' };
          } else {
            style = { stroke: '#8a936a' };
          }
        } else if (edgeFunction.function_type === 'threshold') {
          // Label with threshold and direction
          const threshold = edgeFunction.parameters?.threshold || 0;
          const direction = edgeFunction.parameters?.direction || 'greater';
          label = `T: ${threshold.toFixed(1)} (${direction})`;
          style = { strokeWidth: 2, stroke: '#8f8574' };
        }
        
        transformedEdges.push({
          id: edgeId,
          source: edge.from,
          target: edge.to,
          label,
          labelStyle: { fill: '#5c5c5c', fontWeight: 500, fontSize: 12 },
          style,
          animated: false // Disable animation
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
      <Alert variant="destructive" className={`${className}`}>
        <AlertDescription className="text-[#933a3a]">{error}</AlertDescription>
      </Alert>
    );
  }

  if (causalGraphs.length === 0) {
    return (
      <div className={`text-center p-8 ${className}`}>
        <p className="text-[#8a7f6c]">No causal graphs available for this session.</p>
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
                <span className="text-xs text-[#5c5c5c]">External State</span>
              </div>
              <div className="flex items-center mb-2">
                <div className="w-3 h-3 bg-purple-500 mr-2 rounded-sm"></div>
                <span className="text-xs text-[#5c5c5c]">Internal Affect</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-amber-500 mr-2 rounded-sm"></div>
                <span className="text-xs text-[#5c5c5c]">Behavioral Intention</span>
              </div>
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
} 