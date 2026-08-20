from __future__ import annotations

from dataclasses import dataclass, asdict
from math import floor
from statistics import median
from typing import Iterable


@dataclass
class CostProfile:
    buyer_commission_pct: float = 0.0
    vat_on_commission_pct: float = 0.0
    transfer_cop: int = 0
    taxes_soat_cop: int = 0
    transport_cop: int = 0
    repair_cop: int = 0
    detailing_cop: int = 0
    financing_cop: int = 0
    admin_fee_cop: int = 0
    contingency_cop: int = 0
    target_profit_pct_of_resale: float = 0.12
    target_profit_floor_cop: int = 3_000_000
    quick_sale_discount_pct: float = 0.05
    fasecolda_cap_pct: float = 1.00

    def fixed_costs(self) -> int:
        return sum([self.transfer_cop,self.taxes_soat_cop,self.transport_cop,self.repair_cop,self.detailing_cop,self.financing_cop,self.admin_fee_cop,self.contingency_cop])

    def bid_multiplier(self) -> float:
        commission=max(0.0,self.buyer_commission_pct); vat=max(0.0,self.vat_on_commission_pct)
        return 1.0+commission+(commission*vat)


@dataclass
class MarketEstimate:
    comparable_count:int
    median_asking_cop:int|None
    p25_asking_cop:int|None
    fasecolda_cop:int|None
    quick_sale_cop:int|None
    conservative_resale_cop:int|None
    confidence:float


@dataclass
class Opportunity:
    conservative_resale_cop:int|None
    max_bid_cop:int|None
    current_bid_cop:int|None
    headroom_cop:int|None
    expected_total_cost_cop:int|None
    expected_profit_cop:int|None
    expected_roi_pct:float|None
    margin_on_resale_pct:float|None
    target_profit_cop:int|None
    score:int
    decision:str
    market_confidence:float


def percentile(values:list[int],p:float)->int|None:
    if not values:return None
    xs=sorted(values)
    if len(xs)==1:return xs[0]
    pos=(len(xs)-1)*p; lo=floor(pos); hi=min(lo+1,len(xs)-1); frac=pos-lo
    return int(round(xs[lo]*(1-frac)+xs[hi]*frac))


def estimate_market(asking_prices:Iterable[int],fasecolda_cop:int|None=None,quick_sale_discount_pct:float=0.05,fasecolda_cap_pct:float=1.0)->MarketEstimate:
    prices=sorted(int(x) for x in asking_prices if x and int(x)>0)
    med=int(median(prices)) if prices else None
    p25=percentile(prices,0.25) if prices else None
    market_anchor=p25 or med
    quick=int(round(market_anchor*(1-quick_sale_discount_pct))) if market_anchor else None
    candidates=[x for x in [quick] if x and x>0]
    if fasecolda_cop and fasecolda_cop>0:candidates.append(int(round(fasecolda_cop*fasecolda_cap_pct)))
    conservative=min(candidates) if candidates else None
    if len(prices)>=8:confidence=.90
    elif len(prices)>=5:confidence=.80
    elif len(prices)>=3:confidence=.65
    elif len(prices)>=1:confidence=.45
    else:confidence=0.0
    if fasecolda_cop:confidence=min(1.0,confidence+.10)
    return MarketEstimate(len(prices),med,p25,fasecolda_cop,quick,conservative,confidence)


def total_cost_for_bid(bid_cop:int,profile:CostProfile)->int:
    return int(round(bid_cop*profile.bid_multiplier()+profile.fixed_costs()))


def calculate_opportunity(market:MarketEstimate,current_bid_cop:int|None,profile:CostProfile)->Opportunity:
    resale=market.conservative_resale_cop
    if not resale:return Opportunity(None,None,current_bid_cop,None,None,None,None,None,None,0,"SIN_DATOS",market.confidence)
    target_profit=max(profile.target_profit_floor_cop,int(round(resale*profile.target_profit_pct_of_resale)))
    available=resale-profile.fixed_costs()-target_profit
    max_bid=max(0,int(floor(available/profile.bid_multiplier())))
    total=profit=roi=margin=headroom=None
    if current_bid_cop is not None and current_bid_cop>=0:
        total=total_cost_for_bid(current_bid_cop,profile); profit=resale-total
        roi=(profit/total*100) if total>0 else None; margin=profit/resale*100; headroom=max_bid-current_bid_cop
    score=_score(roi,headroom,resale,market.confidence,market.comparable_count)
    if current_bid_cop is None:decision="ANALIZAR"
    elif current_bid_cop>max_bid:decision="NO_PUJAR"
    elif score>=75:decision="COMPRAR"
    elif score>=55:decision="VIGILAR"
    else:decision="RIESGO"
    return Opportunity(resale,max_bid,current_bid_cop,headroom,total,profit,round(roi,2) if roi is not None else None,round(margin,2) if margin is not None else None,target_profit,score,decision,market.confidence)


def _score(roi_pct:float|None,headroom:int|None,resale:int,confidence:float,comparable_count:int)->int:
    roi_points=0 if roi_pct is None else max(0,min(40,int(round(roi_pct/30*40))))
    headroom_points=0 if headroom is None else max(0,min(25,int(round((headroom/resale if resale else 0)/.20*25))))
    confidence_points=int(round(max(0,min(1,confidence))*25)); comp_points=min(10,comparable_count)
    return max(0,min(100,roi_points+headroom_points+confidence_points+comp_points))
