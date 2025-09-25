#!/usr/bin/env python3
"""
Performance Comparison Script

This script compares the original and optimized SQL maintenance processes
to demonstrate the performance improvements achieved.

Author: Mongrel Data Lab
Date: 2024
"""

import time
import psutil
import os
import sys
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor system performance during script execution"""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
        self.peak_memory = 0
        self.peak_cpu = 0
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = psutil.cpu_percent()
        self.peak_memory = self.start_memory
        self.peak_cpu = self.start_cpu
        logger.info(f"Started monitoring - Memory: {self.start_memory:.1f}MB, CPU: {self.start_cpu:.1f}%")
    
    def update_peak_metrics(self):
        """Update peak memory and CPU usage"""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        current_cpu = psutil.cpu_percent()
        
        self.peak_memory = max(self.peak_memory, current_memory)
        self.peak_cpu = max(self.peak_cpu, current_cpu)
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return performance metrics"""
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        end_cpu = psutil.cpu_percent()
        
        execution_time = end_time - self.start_time
        memory_used = end_memory - self.start_memory
        memory_peak = self.peak_memory - self.start_memory
        
        return {
            'execution_time': execution_time,
            'memory_start': self.start_memory,
            'memory_end': end_memory,
            'memory_used': memory_used,
            'memory_peak': memory_peak,
            'cpu_start': self.start_cpu,
            'cpu_end': end_cpu,
            'cpu_peak': self.peak_cpu
        }


def run_original_script() -> Dict[str, Any]:
    """Run the original SQL maintenance script"""
    logger.info("Running original SQL maintenance script...")
    
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    try:
        # Import and run original script
        sys.path.append('/home/mongreldatalab/mongrel_price_ticker')
        from sql_maintenance import main as original_main
        
        # Capture the original main function behavior
        original_main()
        
        return monitor.stop_monitoring()
        
    except Exception as e:
        logger.error(f"Error running original script: {e}")
        return monitor.stop_monitoring()


def run_optimized_script() -> Dict[str, Any]:
    """Run the optimized SQL maintenance script"""
    logger.info("Running optimized SQL maintenance script...")
    
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    try:
        # Import and run optimized script
        sys.path.append('/home/mongreldatalab/mongrel_price_ticker')
        from sql_maintenance_optimized import main as optimized_main
        
        optimized_main()
        
        return monitor.stop_monitoring()
        
    except Exception as e:
        logger.error(f"Error running optimized script: {e}")
        return monitor.stop_monitoring()


def compare_performance(original_metrics: Dict[str, Any], optimized_metrics: Dict[str, Any]):
    """Compare and display performance metrics"""
    
    logger.info("\n" + "=" * 80)
    logger.info("PERFORMANCE COMPARISON RESULTS")
    logger.info("=" * 80)
    
    # Execution time comparison
    time_improvement = ((original_metrics['execution_time'] - optimized_metrics['execution_time']) / 
                       original_metrics['execution_time'] * 100)
    
    logger.info(f"EXECUTION TIME:")
    logger.info(f"  Original:  {original_metrics['execution_time']:.2f}s")
    logger.info(f"  Optimized: {optimized_metrics['execution_time']:.2f}s")
    logger.info(f"  Improvement: {time_improvement:.1f}% faster")
    
    # Memory usage comparison
    memory_improvement = ((original_metrics['memory_peak'] - optimized_metrics['memory_peak']) / 
                         original_metrics['memory_peak'] * 100) if original_metrics['memory_peak'] > 0 else 0
    
    logger.info(f"\nMEMORY USAGE:")
    logger.info(f"  Original Peak:  {original_metrics['memory_peak']:.1f}MB")
    logger.info(f"  Optimized Peak: {optimized_metrics['memory_peak']:.1f}MB")
    logger.info(f"  Improvement: {memory_improvement:.1f}% less memory")
    
    # CPU usage comparison
    cpu_improvement = ((original_metrics['cpu_peak'] - optimized_metrics['cpu_peak']) / 
                      original_metrics['cpu_peak'] * 100) if original_metrics['cpu_peak'] > 0 else 0
    
    logger.info(f"\nCPU USAGE:")
    logger.info(f"  Original Peak:  {original_metrics['cpu_peak']:.1f}%")
    logger.info(f"  Optimized Peak: {optimized_metrics['cpu_peak']:.1f}%")
    logger.info(f"  Improvement: {cpu_improvement:.1f}% less CPU")
    
    # Overall efficiency score
    efficiency_score = (time_improvement + memory_improvement + cpu_improvement) / 3
    logger.info(f"\nOVERALL EFFICIENCY IMPROVEMENT: {efficiency_score:.1f}%")
    
    logger.info("=" * 80)


def main():
    """Main comparison function"""
    logger.info("Starting performance comparison between original and optimized SQL maintenance scripts")
    
    try:
        # Run original script
        logger.info("\n" + "-" * 40)
        logger.info("RUNNING ORIGINAL SCRIPT")
        logger.info("-" * 40)
        original_metrics = run_original_script()
        
        # Wait a moment between runs
        time.sleep(2)
        
        # Run optimized script
        logger.info("\n" + "-" * 40)
        logger.info("RUNNING OPTIMIZED SCRIPT")
        logger.info("-" * 40)
        optimized_metrics = run_optimized_script()
        
        # Compare results
        compare_performance(original_metrics, optimized_metrics)
        
    except Exception as e:
        logger.error(f"Error during performance comparison: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
