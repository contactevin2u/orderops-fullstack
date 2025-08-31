import Link from 'next/link';
import React from 'react';
import { 
  Truck as TruckIcon, 
  Map as MapIcon, 
  DollarSign as CurrencyDollarIcon, 
  Sparkles as SparklesIcon, 
  ClipboardList as ClipboardDocumentListIcon,
  Users as UserGroupIcon,
  Calendar as CalendarDaysIcon,
  ArrowRight as ArrowRightIcon,
  CheckCircle as CheckCircleIcon
} from 'lucide-react';
import AdminLayout from '@/components/admin/AdminLayout';

export default function AdminIndexPage() {
  const sections = [
    {
      title: 'Driver Operations',
      description: 'Manage your delivery workforce and schedules',
      icon: <TruckIcon className="h-6 w-6" />,
      color: 'from-blue-500 to-cyan-500',
      items: [
        { 
          href: '/admin/drivers', 
          label: 'Driver Management', 
          description: 'Create accounts and manage driver profiles',
          icon: <TruckIcon className="h-5 w-5" />
        },
        { 
          href: '/admin/driver-schedule', 
          label: 'Driver Schedule', 
          description: 'Schedule drivers for daily operations',
          icon: <CalendarDaysIcon className="h-5 w-5" />
        },
        { 
          href: '/admin/routes', 
          label: 'Route Planning', 
          description: 'Create and optimize delivery routes',
          icon: <MapIcon className="h-5 w-5" />
        },
        { 
          href: '/admin/driver-commissions', 
          label: 'Commission Reports', 
          description: 'Track driver earnings and performance',
          icon: <CurrencyDollarIcon className="h-5 w-5" />
        },
      ]
    },
    {
      title: 'Order Assignment', 
      description: 'Unified workflow for automated and manual assignment',
      icon: <SparklesIcon className="h-6 w-6" />,
      color: 'from-purple-500 to-pink-500',
      items: [
        { 
          href: '/admin/unified-assignments', 
          label: 'Unified Assignment Workflow', 
          description: 'Auto-assign orders with AI and create routes automatically',
          icon: <SparklesIcon className="h-5 w-5" />
        },
        { 
          href: '/admin/assign', 
          label: 'Manual Assignment', 
          description: 'Manually assign specific orders when needed',
          icon: <ClipboardDocumentListIcon className="h-5 w-5" />
        },
      ]
    },
    {
      title: 'Administration',
      description: 'System settings and user management',
      icon: <UserGroupIcon className="h-6 w-6" />,
      color: 'from-emerald-500 to-teal-500',
      items: [
        { 
          href: '/admin/users', 
          label: 'User Accounts', 
          description: 'Create admin and cashier accounts',
          icon: <UserGroupIcon className="h-5 w-5" />
        },
      ]
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Header */}
      <div className="mb-12 text-center">
        <div className="mx-auto w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-6">
          <TruckIcon className="h-10 w-10 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
          Welcome to OrderOps
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
          Your complete delivery management system. Schedule drivers, assign orders, and optimize routes with AI-powered intelligence.
        </p>
      </div>

      {/* Feature Sections */}
      <div className="space-y-12">
        {sections.map((section) => (
          <div key={section.title} className="relative">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Section Header */}
              <div className={`bg-gradient-to-r ${section.color} px-6 py-8 text-white`}>
                <div className="flex items-center gap-4 mb-3">
                  {section.icon}
                  <h2 className="text-2xl font-bold">{section.title}</h2>
                </div>
                <p className="text-white/90 text-lg">{section.description}</p>
              </div>

              {/* Cards Grid */}
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {section.items.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="group relative bg-gray-50 dark:bg-gray-700/50 rounded-xl p-6 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 hover:bg-white dark:hover:bg-gray-700 transition-all duration-200 hover:shadow-md"
                    >
                      <div className="flex items-start gap-4">
                        <div className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                          {item.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors mb-2">
                            {item.label}
                          </h3>
                          <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                            {item.description}
                          </p>
                        </div>
                        <ArrowRightIcon className="h-5 w-5 text-gray-400 group-hover:text-blue-500 transition-colors opacity-0 group-hover:opacity-100 transform translate-x-1 group-hover:translate-x-0" />
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Start Guide */}
      <div className="mt-16 bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl p-8 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-blue-500 rounded-lg">
            <CheckCircleIcon className="h-6 w-6 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Quick Start Guide
          </h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { step: '1', title: 'Create Drivers', desc: 'Add driver accounts and profiles' },
            { step: '2', title: 'Schedule Drivers', desc: 'Set daily driver availability' },
            { step: '3', title: 'Assign Orders', desc: 'Use AI or manual assignment' },
            { step: '4', title: 'Track Performance', desc: 'Monitor commissions and routes' }
          ].map((item, index) => (
            <div key={index} className="flex items-start gap-4">
              <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm shrink-0">
                {item.step}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  {item.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

(AdminIndexPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
