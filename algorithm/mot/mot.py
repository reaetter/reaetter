import multiprocessing
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import math
import multiprocessing
from scipy.interpolate import interp1d

def manlio_ft(g, t, g_0=1, g_dot_inf=0, N_f=100, interpolate=True, oversampling=10):
    """ Calculates the Fourier transform of numeric data. (slow version)

    Takes any numeric time-dependent function g(t) that vanishes fot t<0,
    sampled at finite points [g_k,t_k] with k=1...N, and returns its 
    Fourier transform g(omega), together with the frequency range omega 
    defined from 1/t_max to 1/t_min. For details on the numerical procedure,
    refer to Tassieri et al., 2016 (https://doi.org/10.1122/1.4953443).

    Parameters
    ---------
    g : array 
        measured time-dependent variable.
    t : array 
        time array. 
    g_0: 
        value of g at time euqal 0. Can be taken as g[0].
    g_dot_inf:
        value of the time derivative of g at time equal infinity. Can be taken as 0.
    N_f: int
        frequency samples.
    interpolate: bool
        if True, data is interpolated with a cubic spline and re-sampled in log-space.
    oversampling: int
        factor by which the length of the time array is increased for oversampling in log-space.
    """
    
    g=np.array(g)
    t=np.array(t)
    
    if interpolate is True: #输入赋值
        gi = interp1d(t,g,kind='cubic',fill_value='extrapolate')
        t_new = np.logspace(min(np.log10(t)), max(np.log10(t)), len(t)*oversampling) #re-sample t in log space
        g = gi(t_new) # get new g(t) taken at log-space sampled t
        t = t_new
    i = complex(0,1)
    min_omega = 1/max(t)
    max_omega = 1/min(t)
    N_t = len(t)
    omega = np.logspace(np.log10(min_omega), np.log10(max_omega), N_f)
    zero = i*omega*g_0 + (1-np.exp(-i*omega*t[1]))*((g[1]-g_0)/t[1])\
            + g_dot_inf*np.exp(-i*omega*t[N_t-1]) 
    res = np.zeros(len(omega),dtype=complex)
    for w_i, w in enumerate(omega):
         after = 0
         for k in range(2,N_t):
            after+=((g[k] - g[k-1]) / (t[k] - t[k-1])) * (np.exp(-i * w *
            t[k-1])-np.exp(-i * w * t[k]))
         res[w_i]=(zero[w_i]+after)
    return omega, ((res)/(i*omega)**2)

'''
输入为kt,at,将原来sigma0和sigmainf输入框改为kt at
interpolate=true/false,oversampling 次数

在ft位置输出
'''
def mot_processing(df, kt, at, interpolate=False, n_times=10):
    i = complex(0,1)
    time = df[0]
    pai = []
    pai = 1 - df[1]
    # n_times only used when interpolate = True
    omega, res_test = manlio_ft(pai, time, interpolate=interpolate, oversampling=n_times)
    G_star = (kt/(6 * math.pi * at))*(1/(i * omega * res_test) - 1)
    g_p = np.real(G_star)
    g_pp = np.imag(G_star)

    return omega.tolist(), g_p.tolist(), g_pp.tolist()

"""
Using multi-processes to accelerate processing
"""
# Race condition --- lock
def calcu(N_t,g,t,i,w,w_i,lock,zero,res):
        after=0
        for k in range(2, N_t):
            after += ((g[k] - g[k - 1]) / (t[k] - t[k - 1])) * (np.exp(-i * w *t[k - 1]) - np.exp(-i * w * t[k]))
        # print(after)
        
        lock.acquire()
        res[w_i] = after + zero[w_i]
        lock.release()

        return after

def fast_manlio_ft(g, t, g_0=1, g_dot_inf=0, N_f=100, interpolate=True, oversampling=10):
    g = np.array(g)
    t = np.array(t)

    if interpolate is True:
        gi = interp1d(t, g, kind='cubic', fill_value='extrapolate')
        t_new = np.logspace(min(np.log10(t)), max(np.log10(t)), len(t) * oversampling)  # re-sample t in log space
        g = gi(t_new)  # get new g(t) taken at log-space sampled t
        t = t_new

    i = complex(0, 1)
    min_omega = 1 / max(t)
    max_omega = 1 / min(t)
    N_t = len(t)
    omega = np.logspace(np.log10(min_omega), np.log10(max_omega), N_f)

    zero = i * omega * g_0 + (1 - np.exp(-i * omega * t[1])) * ((g[1] - g_0) / t[1]) \
           + g_dot_inf * np.exp(-i * omega * t[N_t - 1])

    res = multiprocessing.Manager().list()
    for idx in range(100):
        res.append(i)

    # setting a lock
    lock = multiprocessing.Manager().Lock()
    # seting a resource pool
    pool = multiprocessing.Pool(processes = 5)
    for w_i, w in enumerate(omega):
        #维持执行的进程总数为processes，当一个进程执行完毕后会添加新的进程进去
        pool.apply_async(calcu, (N_t,g, t, i, w, w_i, lock, zero, res))   

    pool.close()
    pool.join()
    # print("-----------------\n",res)
    # print(len(res))
    return omega, ((res) / (i * omega) ** 2)

def fast_mot_procressing(df, kt, at, interpolate=False, n_times=10):
    i = complex(0, 1)
    time = df[0]
    pai = []
    pai = 1 - df[1]

    omega, res_test = fast_manlio_ft(pai, time, interpolate=interpolate, oversampling=n_times)
    G_star = (kt/(6 * math.pi * at))*(1/(i * omega * res_test) - 1)
    g_p = np.real(G_star)
    g_pp = np.imag(G_star)
    
    return omega.tolist(), g_p.tolist(), g_pp.tolist()

def test(df_news):
    i = complex(0,1)
    kt = 1e-6  #输入赋值
    at = 1e6   #输入赋值
    time = df_news[0]
    pai = []
    pai = 1 - df_news[1]
    omega,res_test = manlio_ft(pai,time,N_f=100,interpolate=True)
    G_star = (kt/(6 * math.pi * at))*(1/(i * omega * res_test) - 1)
    g_p = np.real(G_star)
    g_pp = np.imag(G_star)
    plt.loglog(omega, g_p, '-o', lw=3, color='red',label='$G^{I}$') 
    plt.loglog(omega, g_pp, '-o', lw=3, color='royalblue',label='$G^{II}$')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Moduli (Pa)')
    plt.legend()
    plt.show()

if __name__ == '__main__':
    df_news = pd.read_table('data.txt',sep=' ',header = None)
    test(df_news)
