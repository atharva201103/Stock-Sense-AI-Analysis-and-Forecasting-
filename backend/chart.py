
import matplotlib.pyplot as plt
plt.style.use('seaborn')
plt.figure(figsize=(10, 6))
plt.plot(['SBIN', 'HDFCBANK', 'TCS', 'POWERGRID'], 
         [28940.288, 3100.358, 5448.143, 2918.5], 
         color='red')
plt.title('Portfolio Stocks', fontsize=14)
plt.xlabel('Stocks', fontsize=12)
plt.ylabel('Investment Amount (₹)', fontsize=14)
plt.savefig('media/93d3e55c844e4396a05d56a7509ca054.png')
plt.close()
