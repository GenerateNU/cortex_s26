export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      extracted_files: {
        Row: {
          embedding: string | null
          extracted_json: Json
          file_id: string
          file_name: string | null
          file_type: Database["public"]["Enums"]["file_type_enum"] | null
          processed_at: string | null
          summary: string | null
        }
        Insert: {
          embedding?: string | null
          extracted_json: Json
          file_id: string
          file_name?: string | null
          file_type?: Database["public"]["Enums"]["file_type_enum"] | null
          processed_at?: string | null
          summary?: string | null
        }
        Update: {
          embedding?: string | null
          extracted_json?: Json
          file_id?: string
          file_name?: string | null
          file_type?: Database["public"]["Enums"]["file_type_enum"] | null
          processed_at?: string | null
          summary?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "extracted_files_file_id_fkey"
            columns: ["file_id"]
            isOneToOne: true
            referencedRelation: "raw_files"
            referencedColumns: ["file_id"]
          },
        ]
      }
      file_relationships: {
        Row: {
          confidence_score: number | null
          created_at: string | null
          file_id: string
          relationship_id: string
          source: string | null
        }
        Insert: {
          confidence_score?: number | null
          created_at?: string | null
          file_id: string
          relationship_id: string
          source?: string | null
        }
        Update: {
          confidence_score?: number | null
          created_at?: string | null
          file_id?: string
          relationship_id?: string
          source?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "file_relationships_file_id_fkey"
            columns: ["file_id"]
            isOneToOne: false
            referencedRelation: "raw_files"
            referencedColumns: ["file_id"]
          },
          {
            foreignKeyName: "file_relationships_relationship_id_fkey"
            columns: ["relationship_id"]
            isOneToOne: false
            referencedRelation: "relationships"
            referencedColumns: ["relationship_id"]
          },
        ]
      }
      raw_files: {
        Row: {
          file_id: string
          file_link: string
          file_name: string
          uploaded_at: string | null
        }
        Insert: {
          file_id?: string
          file_link: string
          file_name: string
          uploaded_at?: string | null
        }
        Update: {
          file_id?: string
          file_link?: string
          file_name?: string
          uploaded_at?: string | null
        }
        Relationships: []
      }
      relationships: {
        Row: {
          relationship_description: string
          relationship_id: string
          relationship_name: string
        }
        Insert: {
          relationship_description: string
          relationship_id?: string
          relationship_name: string
        }
        Update: {
          relationship_description?: string
          relationship_id?: string
          relationship_name?: string
        }
        Relationships: []
      }
      webhook_config: {
        Row: {
          key: string
          updated_at: string | null
          value: string | null
        }
        Insert: {
          key: string
          updated_at?: string | null
          value?: string | null
        }
        Update: {
          key?: string
          updated_at?: string | null
          value?: string | null
        }
        Relationships: []
      }
      classifications: {
        Row: {
          id: string
          created_at: string
          name: string
          tenant_id: string
        }
        Insert: {
          id?: string
          created_at?: string
          name: string
          tenant_id?: string
        }
        Update: {
          id?: string
          created_at?: string
          name?: string
          tenant_id?: string
        }
        Relationships: []
      }
      migrations: {
        Row: {
          id: string
          created_at: string
          name: string
          sql: string
          sequence: number
          tenant_id: string
        }
        Insert: {
          id?: string
          created_at?: string
          name: string
          sql: string
          sequence: number
          tenant_id?: string
        }
        Update: {
          id?: string
          created_at?: string
          name?: string
          sql?: string
          sequence?: number
          tenant_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      match_extracted_files: {
        Args: {
          match_count: number
          match_threshold: number
          query_embedding: string
        }
        Returns: {
          extracted_json: Json
          file_id: string
          file_name: string
          file_type: Database["public"]["Enums"]["file_type_enum"]
          similarity: number
          summary: string
        }[]
      }
      update_webhook_config: {
        Args: { secret: string; url: string }
        Returns: undefined
      }
    }
    Enums: {
      file_type_enum: "RFQ" | "PO" | "ProdSpec" | "Sales" | "Customers"
      relationship_source_enum: "manual" | "ai_inference" | "filename-rule"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      file_type_enum: ["RFQ", "PO", "ProdSpec", "Sales", "Customers"],
      relationship_source_enum: ["manual", "ai_inference", "filename-rule"],
    },
  },
} as const

