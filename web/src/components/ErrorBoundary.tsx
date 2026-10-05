import React from "react";
export class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean}> {
  state = {hasError: false};
  static getDerivedStateFromError(){ return {hasError: true};}
  componentDidCatch(e:any){ console.error(e); }
  render(){
    if(this.state.hasError) return <div className="p-6 bg-slate-900 border border-rose-700 rounded-xl text-center space-y-3">
      <div className="text-rose-400 font-mono font-bold">Something went wrong.</div>
      <div className="text-slate-400 text-xs">The current view could not be rendered.</div>
      <button onClick={()=>this.setState({hasError:false})} className="px-3 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white">Retry</button>
      <button onClick={()=>window.location.href="/overview"} className="ml-2 px-3 py-1 bg-indigo-600 rounded text-xs text-white">Return to Overview</button>
    </div>;
    return this.props.children;
  }
}
