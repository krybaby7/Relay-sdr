import { Component, useEffect, useRef } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { label } from './api';

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, string> = {
    grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
    people: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.8M16 3.2a4 4 0 0 1 0 7.6',
    phone: 'M5 3h4l2 5-3 2a16 16 0 0 0 6 6l2-3 5 2v4a2 2 0 0 1-2 2C9 21 3 15 3 5a2 2 0 0 1 2-2z',
    book: 'M4 3h12a3 3 0 0 1 3 3v15H7a3 3 0 0 1-3-3V3zM4 17h15M8 7h7M8 11h5',
    link: 'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2',
    spark: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3z',
    search: 'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
    sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6',
    plus: 'M12 5v14M5 12h14',
    check: 'm4 12 5 5L20 6',
    close: 'M6 6l12 12M18 6 6 18',
    arrow: 'M5 12h14m-6-6 6 6-6 6',
    lock: 'M5 10h14v11H5zM8 10V6a4 4 0 0 1 8 0v4',
    pin: 'M9 3h6l-1 6 4 4H6l4-4-1-6M12 13v8',
    clock: 'M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.grid} /></svg>;
}
export function Badge({ value, children }: { value?: string; children?: ReactNode }) { return <span className={`badge tone-${value || 'neutral'}`}>{children || label(value)}</span>; }
export function Empty({ title = 'Nothing to show yet', text = 'Captured activity will appear here. No sample records are added to your real pipeline.', action }: { title?: string; text?: string; action?: ReactNode }) {
  return <div className="empty"><span className="empty-icon"><Icon name="grid" size={25}/></span><h3>{title}</h3><p>{text}</p>{action}</div>;
}
export function Modal({ title, children, close, wide = false }: { title: string; children: ReactNode; close: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current; const focused = document.activeElement as HTMLElement | null;
    dialog?.showModal();
    return () => { dialog?.close(); focused?.focus(); };
  }, []);
  return <dialog ref={ref} className={`modal ${wide ? 'wide' : ''}`} onCancel={event => { event.preventDefault(); close(); }} aria-label={title}>
    <header className="modal-header"><h2>{title}</h2><button className="icon-button" aria-label={`Close ${title}`} onClick={close}><Icon name="close"/></button></header>
    <div className="modal-content">{children}</div>
  </dialog>;
}
export class WidgetBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) { /* Do not log CRM records or provider responses. */ }
  render() { return this.state.failed ? <Empty title="This widget could not render" text="Your saved workspace and records are unchanged. Reload to retry."/> : this.props.children; }
}
