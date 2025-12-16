import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json

class NBPTTokenomics:
    def __init__(self):
        self.total_supply = 100_000_000  # 100M tokens
        self.allocations = {
            'Founders/Team': {'tokens': 20_000_000, 'percent': 20, 'vesting_months': 36, 'cliff_months': 6},
            'Ecosystem Development': {'tokens': 25_000_000, 'percent': 25, 'vesting_months': 36, 'cliff_months': 0},
            'Strategic Investors': {'tokens': 15_000_000, 'percent': 15, 'vesting_months': 18, 'cliff_months': 3},
            'Public ICO': {'tokens': 12_000_000, 'percent': 12, 'vesting_months': 0, 'cliff_months': 0},
            'AI Agent Rewards': {'tokens': 10_000_000, 'percent': 10, 'vesting_months': 24, 'cliff_months': 0},
            'Community Incentives': {'tokens': 8_000_000, 'percent': 8, 'vesting_months': 24, 'cliff_months': 0},
            'Treasury Reserve': {'tokens': 7_000_000, 'percent': 7, 'vesting_months': 60, 'cliff_months': 12},
            'Liquidity Provision': {'tokens': 3_000_000, 'percent': 3, 'vesting_months': 12, 'cliff_months': 0}
        }
        
    def calculate_monthly_releases(self, months=36):
        """Calculate token releases for each month"""
        monthly_data = []
        
        for month in range(1, months + 1):
            month_release = 0
            circulating_supply = 12_000_000 + 3_000_000  # ICO + Liquidity at launch
            
            for category, details in self.allocations.items():
                if category in ['Public ICO', 'Liquidity Provision']:
                    continue  # Already counted
                    
                cliff = details['cliff_months']
                vesting = details['vesting_months']
                total_tokens = details['tokens']
                
                if month > cliff and month <= cliff + vesting:
                    monthly_release = total_tokens / vesting
                    month_release += monthly_release
            
            # Calculate cumulative circulating supply
            if month == 1:
                cumulative = 15_000_000  # ICO + Liquidity
            else:
                prev_cumulative = monthly_data[-1]['cumulative_circulating']
                cumulative = prev_cumulative + month_release
            
            monthly_data.append({
                'month': month,
                'monthly_release': month_release,
                'cumulative_circulating': cumulative,
                'circulating_percent': (cumulative / self.total_supply) * 100,
                'locked_tokens': self.total_supply - cumulative
            })
        
        return monthly_data
    
    def calculate_token_value_projections(self, monthly_data):
        """Calculate projected token values based on utility and scarcity"""
        projections = []
        
        for data in monthly_data:
            month = data['month']
            circulating = data['cumulative_circulating']
            
            # Base utility value (grows with platform adoption)
            utility_multiplier = 1 + (month * 0.1)  # 10% growth per month
            
            # Scarcity premium (inverse relationship with circulating supply)
            scarcity_premium = (self.total_supply / circulating) * 0.5
            
            # Market adoption factor
            adoption_factor = min(month / 12, 3.0)  # Caps at 3x after 12 months
            
            # Calculate projected price
            base_price = 1.00  # $1 ICO price
            projected_price = base_price * utility_multiplier * scarcity_premium * adoption_factor
            
            # Market cap calculation
            market_cap = projected_price * circulating
            
            projections.append({
                'month': month,
                'projected_price': round(projected_price, 2),
                'market_cap': round(market_cap, 0),
                'utility_multiplier': round(utility_multiplier, 2),
                'scarcity_premium': round(scarcity_premium, 2)
            })
        
        return projections
    
    def generate_burn_schedule(self, monthly_data):
        """Calculate quarterly token burns"""
        burns = []
        
        for quarter in range(1, 13):  # 3 years = 12 quarters
            month = quarter * 3
            if month <= len(monthly_data):
                circulating = monthly_data[month-1]['cumulative_circulating']
                
                # Burn calculation: 0.5-1% of circulating supply quarterly
                burn_rate = 0.0075  # 0.75% quarterly average
                quarterly_burn = circulating * burn_rate
                
                burns.append({
                    'quarter': quarter,
                    'month': month,
                    'tokens_burned': round(quarterly_burn, 0),
                    'burn_rate_percent': burn_rate * 100
                })
        
        return burns
    
    def export_to_csv(self, monthly_data, projections, burns):
        """Export all data to CSV files"""
        # Monthly releases
        df_monthly = pd.DataFrame(monthly_data)
        df_monthly.to_csv('NBPT_Monthly_Releases.csv', index=False)
        
        # Price projections
        df_projections = pd.DataFrame(projections)
        df_projections.to_csv('NBPT_Price_Projections.csv', index=False)
        
        # Burn schedule
        df_burns = pd.DataFrame(burns)
        df_burns.to_csv('NBPT_Burn_Schedule.csv', index=False)
        
        print("✅ CSV files generated:")
        print("- NBPT_Monthly_Releases.csv")
        print("- NBPT_Price_Projections.csv") 
        print("- NBPT_Burn_Schedule.csv")
    
    def generate_summary_report(self, monthly_data, projections, burns):
        """Generate executive summary"""
        final_month = monthly_data[-1]
        final_projection = projections[-1]
        total_burns = sum([b['tokens_burned'] for b in burns])
        
        summary = f"""
🚀 NBPT ULTRA-SCARCE TOKENOMICS SUMMARY

📊 SUPPLY METRICS (36 months):
• Total Supply: {self.total_supply:,} NBPT (Fixed Forever)
• Initial Circulating: 15,000,000 NBPT (15%)
• Final Circulating: {final_month['cumulative_circulating']:,.0f} NBPT ({final_month['circulating_percent']:.1f}%)
• Permanently Locked: {final_month['locked_tokens']:,.0f} NBPT ({100-final_month['circulating_percent']:.1f}%)

💰 VALUE PROJECTIONS:
• ICO Launch Price: $1.00
• 36-Month Target: ${final_projection['projected_price']}
• Peak Market Cap: ${final_projection['market_cap']:,.0f}
• Total ROI Potential: {((final_projection['projected_price'] - 1) * 100):.0f}%

🔥 DEFLATIONARY MECHANICS:
• Total Tokens Burned: {total_burns:,.0f} NBPT
• Effective Supply Reduction: {(total_burns/self.total_supply)*100:.2f}%
• Net Circulating (Post-Burns): {final_month['cumulative_circulating'] - total_burns:,.0f} NBPT

🎯 SCARCITY ADVANTAGES:
• Bitcoin Comparison: 21M BTC vs 100M NBPT
• Ethereum Comparison: 120M ETH vs 100M NBPT  
• Utility Demand: Every platform transaction requires NBPT
• AI Optimization: Stephanie.ai manages supply dynamics

💎 INVESTMENT THESIS:
"NBPT represents the world's first AI-governed, ultra-scarce token backed by 
$289M+ in real estate assets and construction projects. With only 100M tokens 
ever to exist and massive utility demand, NBPT is positioned for explosive growth."

🚀 September 5th ICO: The Ultra-Scarce Revolution Begins!
        """
        
        with open('NBPT_Executive_Summary.txt', 'w') as f:
            f.write(summary)
        
        print(summary)
        return summary

# Run the complete tokenomics analysis
if __name__ == "__main__":
    print("🚀 Generating NBPT Ultra-Scarce Tokenomics Model...")
    
    nbpt = NBPTTokenomics()
    
    # Calculate monthly releases
    monthly_data = nbpt.calculate_monthly_releases(36)
    
    # Calculate price projections  
    projections = nbpt.calculate_token_value_projections(monthly_data)
    
    # Calculate burn schedule
    burns = nbpt.generate_burn_schedule(monthly_data)
    
    # Export data
    nbpt.export_to_csv(monthly_data, projections, burns)
    
    # Generate summary
    summary = nbpt.generate_summary_report(monthly_data, projections, burns)
    
    print("\n💎 NBPT Ultra-Scarce Tokenomics Model Complete!")
    print("📁 All files saved to tokenomics/ directory")
