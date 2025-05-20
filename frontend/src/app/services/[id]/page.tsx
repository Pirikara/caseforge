"use client"

import { useParams } from 'next/navigation';
import React, { useState } from 'react';
import { ServiceDetailLayout } from '@/components/management/ServiceDetailLayout';
import SchemaManagementTab from '@/components/tabs/SchemaManagementTab';
import EndpointManagementTab from '@/components/tabs/EndpointManagementTab';
import TestSuiteManagementTab from '@/components/tabs/TestSuiteManagementTab';
import { TabsContent } from '@/components/ui/tabs';
import { useServices } from '@/hooks/useServices';

export default function ServiceDetailPage() {
  const params = useParams();
  const serviceId = params.id as string;
  const [activeTab, setActiveTab] = useState<string>('schema');
  const { services } = useServices();

  const service = React.useMemo(() => {
    if (!services) return null;
    return services.find(s => s.id === serviceId);
  }, [services, serviceId]);

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    const url = new URL(window.location.href);
    url.searchParams.set('tab', value);
    window.history.replaceState({}, '', url.toString());
  };

  return (
    <div className="space-y-6">
      <ServiceDetailLayout
        activeTab={activeTab}
        onTabChange={handleTabChange}
      >
        <TabsContent value="schema" className="space-y-4">
          <SchemaManagementTab serviceId={serviceId} />
        </TabsContent>

        <TabsContent value="endpoints" className="space-y-4">
          <EndpointManagementTab serviceId={serviceId} />
        </TabsContent>

        <TabsContent value="test-suites" className="space-y-4">
          {service && <TestSuiteManagementTab serviceId={serviceId} service={service} />}
        </TabsContent>
      </ServiceDetailLayout>
    </div>
  );
}
