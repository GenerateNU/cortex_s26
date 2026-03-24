import { useMemo } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  type Node, 
  type Edge,
  ConnectionLineType
} from 'reactflow';
import 'reactflow/dist/style.css';

interface GraphData {
  nodes: {
    id: string
    label: string
    type: 'file' | 'relationship'
    description?: string
  }[]
  edges: {
    id: string
    source: string
    target: string
    confidence?: number
  }[]
}

interface RelationshipGraphProps {
  data?: GraphData
  isLoading?: boolean
}

export function RelationshipGraph({ data, isLoading }: RelationshipGraphProps) {
  // Simple layout calculation
  const { nodes, edges } = useMemo(() => {
    if (!data || !data.nodes) return { nodes: [], edges: [] };

    const relationshipNodes = data.nodes.filter(n => n.type === 'relationship');
    const fileNodes = data.nodes.filter(n => n.type === 'file');

    const centerX = 400;
    const centerY = 300;
    const radius = 250;

    const flowNodes: Node[] = [];
    
    // Place relationships in the center (or close to it)
    relationshipNodes.forEach((node, index) => {
        // distribute them in a small inner circle if multiple, or just center
        const innerRadius = 50;
        const angle = (index / relationshipNodes.length) * 2 * Math.PI;
        
        flowNodes.push({
            id: node.id,
            data: { label: node.label },
            position: relationshipNodes.length === 1 
                ? { x: centerX, y: centerY }
                : { 
                    x: centerX + innerRadius * Math.cos(angle), 
                    y: centerY + innerRadius * Math.sin(angle) 
                  },
            style: { 
                background: '#1e293b', 
                color: '#94a3b8', 
                border: '1px solid #475569',
                borderRadius: '8px',
                padding: '10px',
                width: 150,
                textAlign: 'center',
                fontSize: '12px'
            },
        });
    });

    // Place files in a larger outer circle
    fileNodes.forEach((node, index) => {
        const angle = (index / fileNodes.length) * 2 * Math.PI;
        flowNodes.push({
            id: node.id,
            data: { label: node.label }, // truncate if needed
            position: { 
                x: centerX + radius * Math.cos(angle), 
                y: centerY + radius * Math.sin(angle) 
            },
            style: { 
                background: '#0f172a', 
                color: '#e2e8f0', 
                border: '1px solid #334155',
                borderRadius: '50%',
                width: 60,
                height: 60,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '10px',
                textAlign: 'center'
            },
        });
    });

    const flowEdges: Edge[] = data.edges.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: ConnectionLineType.Straight,
        style: { stroke: '#475569', strokeWidth: 1 },
        animated: true,
    }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [data]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full text-slate-500">
                Loading Graph...
            </div>
        );
    }
    
    if (!data?.nodes || data.nodes.length === 0) {
        return (
            <div className="flex items-center justify-center h-full text-slate-500">
                No relationships found. Run "Analyze" on your files.
            </div>
        )
    }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-right"
        className="bg-slate-900"
      >
        <Background color="#334155" gap={16} />
        <Controls className="bg-slate-800 border-slate-700 fill-slate-300" />
      </ReactFlow>
    </div>
  );
}
