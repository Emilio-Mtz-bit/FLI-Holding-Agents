import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface Props {
  title: string;
  value: string;
  sub?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export default function MetricCard({ title, value, sub, trend }: Props) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{title}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
        {(sub || trend) && (
          <div className="flex items-center gap-1 mt-1">
            {trend === 'up' && <TrendingUp size={14} className="text-emerald-500" />}
            {trend === 'down' && <TrendingDown size={14} className="text-rose-500" />}
            {sub && <p className="text-sm text-muted-foreground">{sub}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
