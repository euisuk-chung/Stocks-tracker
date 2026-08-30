import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { ChartPoint } from '../lib/reports';

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

export default function TrendChart({ points, symbol }: { points: ChartPoint[]; symbol: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || points.length === 0) return;
    const chart = echarts.init(ref.current, undefined, { renderer: 'canvas' });
    chart.setOption({
      animation: false,
      grid: { left: 4, right: 10, top: 42, bottom: 46, containLabel: true },
      legend: {
        top: 0,
        left: 'center',
        itemWidth: 14,
        itemHeight: 3,
        itemGap: 8,
        textStyle: { color: '#9aada7', fontSize: 9 },
      },
      tooltip: { trigger: 'axis', backgroundColor: '#14231f', borderColor: '#304a41', textStyle: { color: '#f2f7f5' } },
      xAxis: {
        type: 'category',
        data: points.map((p) => p.date),
        axisLine: { lineStyle: { color: '#31423d' } },
        axisLabel: {
          color: '#7f958d',
          interval: 9,
          rotate: 35,
          margin: 12,
          hideOverlap: true,
          formatter: (value: string) => value.slice(5),
        },
      },
      yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: 'rgba(208,238,225,.08)' } }, axisLabel: { color: '#7f958d' } },
      series: [
        { name: '종가', type: 'line', data: points.map((p) => p.close), symbol: 'none', lineStyle: { color: '#f1f7f4', width: 2.5 } },
        { name: '1개월선 · 20거래일', type: 'line', data: points.map((p) => p.ma20 ?? null), symbol: 'none', connectNulls: false, lineStyle: { color: '#83e6b4', width: 1.5 } },
        { name: '2개월선 · 40거래일', type: 'line', data: points.map((p) => p.ma40 ?? null), symbol: 'none', connectNulls: false, lineStyle: { color: '#f4c96f', width: 1.5 } },
      ],
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => { window.removeEventListener('resize', resize); chart.dispose(); };
  }, [points, symbol]);

  if (points.length === 0) return <div className="chart-empty">차트 데이터 준비 중</div>;
  return <div ref={ref} className="trend-chart" role="img" aria-label={`${symbol} 최근 3개월 종가, 1개월선(20거래일 종가 평균), 2개월선(40거래일 종가 평균) 차트`} />;
}
