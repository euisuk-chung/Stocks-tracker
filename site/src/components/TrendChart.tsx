import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { ChartPoint } from '../lib/reports';

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

export default function TrendChart({ points, symbol }: { points: ChartPoint[]; symbol: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || points.length === 0) return;
    const chart = echarts.init(ref.current, undefined, { renderer: 'canvas' });
    chart.setOption({
      animation: false,
      grid: { left: 4, right: 10, top: 12, bottom: 20, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: '#14231f', borderColor: '#304a41', textStyle: { color: '#f2f7f5' } },
      xAxis: { type: 'category', data: points.map((p) => p.date), axisLine: { lineStyle: { color: '#31423d' } }, axisLabel: { color: '#7f958d', interval: 6 } },
      yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: 'rgba(208,238,225,.08)' } }, axisLabel: { color: '#7f958d' } },
      series: [
        { name: `${symbol} 종가`, type: 'line', data: points.map((p) => p.close), symbol: 'none', lineStyle: { color: '#f1f7f4', width: 2.5 } },
        { name: '20일선', type: 'line', data: points.map((p) => p.ma20 ?? null), symbol: 'none', connectNulls: false, lineStyle: { color: '#83e6b4', width: 1.5 } },
        { name: '30일선', type: 'line', data: points.map((p) => p.ma30 ?? null), symbol: 'none', connectNulls: false, lineStyle: { color: '#f4c96f', width: 1.5 } },
      ],
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => { window.removeEventListener('resize', resize); chart.dispose(); };
  }, [points, symbol]);

  if (points.length === 0) return <div className="chart-empty">차트 데이터 준비 중</div>;
  return <div ref={ref} className="trend-chart" role="img" aria-label={`${symbol} 최근 3개월 종가와 20일·30일 이동평균 차트`} />;
}
