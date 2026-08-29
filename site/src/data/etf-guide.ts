export interface EtfReference {
  ticker: string;
  name: string;
  expenseRatio: string;
  inception: string;
  distinction: string;
  comparisonUse: string;
  sourceUrl: string;
}

export interface EtfFamily {
  familyId: string;
  indexName: string;
  plainDescription: string;
  concentration: string;
  funds: EtfReference[];
}

export const etfGuideVerifiedAt = '2026-08-29';

export const etfFamilies: EtfFamily[] = [
  {
    familyId: 'nasdaq-100',
    indexName: 'Nasdaq-100',
    plainDescription: 'Nasdaq에 상장된 비금융 대형주 100곳을 시가총액 중심으로 담습니다.',
    concentration: '대형 성장주와 기술 관련 기업 비중이 높아 S&P 500보다 쏠림과 변동이 클 수 있습니다.',
    funds: [
      {
        ticker: 'QQQ',
        name: 'Invesco QQQ',
        expenseRatio: '0.18%',
        inception: '1999',
        distinction: '오래된 대표 상품. 같은 지수를 추종하는 QQQM과 먼저 비용·거래 편의를 비교합니다.',
        comparisonUse: '활발한 거래와 옵션 활용 여부까지 확인할 때',
        sourceUrl: 'https://www.invesco.com/qqq-etf/en/home.html',
      },
      {
        ticker: 'QQQM',
        name: 'Invesco Nasdaq 100 ETF',
        expenseRatio: '0.15%',
        inception: '2020',
        distinction: 'QQQ와 같은 Nasdaq-100을 추종하면서 공시 보수가 더 낮습니다.',
        comparisonUse: '같은 지수를 장기 보유할 때 비용부터 비교할 때',
        sourceUrl: 'https://www.invesco.com/us-rest/contentdetail?contentId=5b4d8e58e0737710VgnVCM1000006e36b50aRCRD&dnsName=us',
      },
    ],
  },
  {
    familyId: 'sp-500',
    indexName: 'S&P 500',
    plainDescription: '미국을 대표하는 대형 기업 약 500곳을 시가총액 비중으로 담습니다.',
    concentration: '네 상품의 지수 노출은 매우 비슷하지만 보수, 거래량, 스프레드, 옵션 유무와 운용사가 다릅니다.',
    funds: [
      {
        ticker: 'SPY',
        name: 'State Street SPDR S&P 500 ETF Trust',
        expenseRatio: '0.0945%',
        inception: '1993',
        distinction: '미국 최초의 ETF로 알려진 오래된 대표 상품이며 옵션이 상장돼 있습니다.',
        comparisonUse: '거래 편의와 옵션 시장까지 함께 볼 때',
        sourceUrl: 'https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy',
      },
      {
        ticker: 'VOO',
        name: 'Vanguard S&P 500 ETF',
        expenseRatio: '0.03%',
        inception: '2010',
        distinction: 'S&P 500을 추종하는 저비용 상품입니다.',
        comparisonUse: '장기 보유 비용과 Vanguard 상품 구조를 볼 때',
        sourceUrl: 'https://investor.vanguard.com/investment-products/etfs/profile/voo',
      },
      {
        ticker: 'IVV',
        name: 'iShares Core S&P 500 ETF',
        expenseRatio: '0.03%',
        inception: '2000',
        distinction: 'BlackRock iShares의 S&P 500 저비용 상품입니다.',
        comparisonUse: '장기 보유 비용과 iShares 상품 구조를 볼 때',
        sourceUrl: 'https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf',
      },
      {
        ticker: 'SPYM',
        name: 'State Street SPDR Portfolio S&P 500 ETF',
        expenseRatio: '0.02%',
        inception: '2005',
        distinction: '같은 운용사의 SPY와 별도로 제공되는 저비용 S&P 500 상품입니다.',
        comparisonUse: '같은 지수 안에서 공시 보수를 우선 비교할 때',
        sourceUrl: 'https://www.ssga.com/us/en/individual/etfs/state-street-spdr-portfolio-sp-500-etf-spym',
      },
    ],
  },
];

export const lookAlikeWarnings = [
  {
    tickers: 'QEW',
    label: '같은 100곳, 다른 비중',
    description: 'Nasdaq-100 종목을 거의 같은 비중으로 담아 QQQ·QQQM과 종목별 쏠림이 다릅니다.',
    sourceUrl: 'https://www.invesco.com/us/en/insights/broaden-exposure-nasdaq-100.html',
  },
  {
    tickers: 'QQQJ',
    label: '아예 다른 100곳',
    description: 'Nasdaq-100 다음 순위인 101~200번째 비금융 기업을 담는 별도 지수 상품입니다.',
    sourceUrl: 'https://www.invesco.com/us-rest/contentdetail?contentId=1d4d8e58e0737710VgnVCM1000006e36b50aRCRD&dnsName=us',
  },
  {
    tickers: 'TQQQ · PSQ',
    label: '일간 레버리지·인버스',
    description: '각각 Nasdaq-100의 하루 수익률 3배, 반대 방향 1배를 목표로 합니다. 여러 날의 누적 수익률이 단순 배수가 되지 않을 수 있습니다.',
    sourceUrl: 'https://www.proshares.com/strategies/nasdaq-100-etfs',
  },
];
