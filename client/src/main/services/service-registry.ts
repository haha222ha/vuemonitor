export class ServiceRegistry {
  private static instance: ServiceRegistry;
  private services: Map<string, any> = new Map();

  private constructor() {}

  public static getInstance(): ServiceRegistry {
    if (!ServiceRegistry.instance) {
      ServiceRegistry.instance = new ServiceRegistry();
    }
    return ServiceRegistry.instance;
  }

  public register(name: string, service: any): void {
    this.services.set(name, service);
  }

  public get<T>(name: string): T {
    const service = this.services.get(name);
    if (!service) {
      throw new Error(`Service '${name}' not found`);
    }
    return service as T;
  }

  public has(name: string): boolean {
    return this.services.has(name);
  }

  public list(): string[] {
    return Array.from(this.services.keys());
  }
}

// Export a singleton instance for convenience
export const serviceRegistry = ServiceRegistry.getInstance();