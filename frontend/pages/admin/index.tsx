import Link from 'next/link';
import React from 'react';
import { 
  Truck, 
  Map, 
  DollarSign, 
  Sparkles, 
  ClipboardList,
  Users,
  Calendar,
  ArrowRight,
  Zap,
  BarChart3,
  Settings,
  Clock
} from 'lucide-react';
import AdminLayout from '@/components/admin/AdminLayout';

export default function AdminIndexPage() {
  const quickActions = [
    {
      title: 'Auto-Assign Orders',
      description: 'AI-powered order assignment',
      href: '/admin/unified-assignments',
      icon: Sparkles,
      color: 'bg-gradient-to-br from-purple-500 to-indigo-600',
      badge: 'AI Powered'
    },
    {
      title: 'Schedule Drivers',
      description: 'Manage daily operations',
      href: '/admin/driver-schedule',
      icon: Calendar,
      color: 'bg-gradient-to-br from-blue-500 to-cyan-600',
      badge: 'Today'
    },
    {
      title: 'Driver Management',
      description: 'Manage your workforce',
      href: '/admin/drivers',
      icon: Truck,
      color: 'bg-gradient-to-br from-emerald-500 to-teal-600',
      badge: 'Active'
    },
    {
      title: 'Route Planning',
      description: 'Optimize delivery routes',
      href: '/admin/routes',
      icon: Map,
      color: 'bg-gradient-to-br from-orange-500 to-red-600',
      badge: 'Live'
    }
  ];

  const modules = [
    {
      category: 'Operations',
      items: [
        {
          title: 'Driver Management',
          description: 'Create and manage driver accounts',
          href: '/admin/drivers',
          icon: Truck
        },
        {
          title: 'Driver Schedule',
          description: 'Set daily availability patterns',
          href: '/admin/driver-schedule',
          icon: Calendar
        },
        {
          title: 'Route Planning',
          description: 'Create optimized delivery routes',
          href: '/admin/routes',
          icon: Map
        },
        {
          title: 'Manual Assignment',
          description: 'Assign orders to specific drivers',
          href: '/admin/assign',
          icon: ClipboardList
        }
      ]
    },
    {
      category: 'Analytics',
      items: [
        {
          title: 'Commission Reports',
          description: 'Track driver earnings and performance',
          href: '/admin/driver-commissions',
          icon: DollarSign
        },
        {
          title: 'Performance Analytics',
          description: 'Monitor delivery metrics',
          href: '/admin/analytics',
          icon: BarChart3
        }
      ]
    },
    {
      category: 'Administration',
      items: [
        {
          title: 'User Management',
          description: 'Manage admin and cashier accounts',
          href: '/admin/users',
          icon: Users
        },
        {
          title: 'System Settings',
          description: 'Configure application settings',
          href: '/admin/settings',
          icon: Settings
        }
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                OrderOps Dashboard
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                Manage your delivery operations with AI-powered efficiency
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-1 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="h-4 w-4" />
                <span>Last updated: {new Date().toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quick Actions */}
        <div className="mb-12">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <Link
                  key={index}
                  href={action.href}
                  className="group relative overflow-hidden rounded-xl p-6 text-white transition-all duration-200 hover:scale-[1.02] hover:shadow-xl"
                >
                  <div className={`absolute inset-0 ${action.color}`} />
                  <div className="relative">
                    <div className="flex items-center justify-between mb-4">
                      <Icon className="h-8 w-8" />
                      <span className="px-2 py-1 bg-white/20 rounded-full text-xs font-medium">
                        {action.badge}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold mb-2">{action.title}</h3>
                    <p className="text-white/80 text-sm">{action.description}</p>
                    <ArrowRight className="h-4 w-4 mt-4 transition-transform group-hover:translate-x-1" />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Modules */}
        <div className="space-y-8">
          {modules.map((module, moduleIndex) => (
            <div key={moduleIndex}>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                {module.category}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {module.items.map((item, itemIndex) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={itemIndex}
                      href={item.href}
                      className="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 transition-all duration-200 hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg"
                    >
                      <div className="flex items-start space-x-4">
                        <div className="flex-shrink-0">
                          <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-gray-100 dark:bg-gray-700 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
                            <Icon className="h-5 w-5 text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-base font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            {item.title}
                          </h3>
                          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                            {item.description}
                          </p>
                        </div>
                        <div className="flex-shrink-0">
                          <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-blue-500 transition-all duration-200 group-hover:translate-x-1" />
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Getting Started */}
        <div className="mt-12 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-8 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center space-x-3 mb-6">
            <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-blue-500">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Getting Started
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { step: '01', title: 'Add Drivers', desc: 'Create driver accounts and profiles' },
              { step: '02', title: 'Set Schedules', desc: 'Define daily driver availability' },
              { step: '03', title: 'Auto-Assign', desc: 'Let AI handle order assignments' },
              { step: '04', title: 'Monitor Progress', desc: 'Track performance and earnings' }
            ].map((item, index) => (
              <div key={index} className="relative">
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="flex items-center justify-center h-8 w-8 rounded-full bg-blue-500 text-white text-sm font-bold">
                      {item.step}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      {item.title}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {item.desc}
                    </p>
                  </div>
                </div>
                {index < 3 && (
                  <div className="hidden lg:block absolute top-4 left-full w-full h-0.5 bg-blue-200 dark:bg-blue-800 -ml-4 -mr-4" />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

(AdminIndexPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
