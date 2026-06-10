import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { compact, pct } from '@/lib/format';

interface Props {
  sucursal: string;
  currentTicket: number;
  requiredTicket: number;
  deltaPercent: number;
  currentEbitda: number;
  targetEbitda: number;
}

export default function BreakEvenCard({
  sucursal, currentTicket, requiredTicket, deltaPercent, currentEbitda, targetEbitda,
}: Props) {
  const needsIncrease = requiredTicket > currentTicket;
  return (
    <Card>
      <CardContent className="pt-4 space-y-2">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-sm">{sucursal}</p>
          <Badge variant={needsIncrease ? 'destructive' : 'default'}>
            {needsIncrease ? '+' : ''}{pct(deltaPercent)} ticket
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="flex justify-between">
            <span>Current ticket</span><span className="font-medium text-foreground">{compact(currentTicket)}</span>
          </div>
          <div className="flex justify-between">
            <span>Required ticket</span>
            <span className={`font-medium ${needsIncrease ? 'text-rose-500' : 'text-emerald-600'}`}>
              {compact(requiredTicket)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Current EBITDA</span><span className="font-medium text-foreground">{compact(currentEbitda)}</span>
          </div>
          <div className="flex justify-between">
            <span>Target EBITDA</span><span className="font-medium text-foreground">{compact(targetEbitda)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
