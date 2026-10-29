export interface paths {
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analyses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Analyses */
        get: operations["list_analyses_api_v1_analyses_get"];
        put?: never;
        /** Create Analysis */
        post: operations["create_analysis_api_v1_analyses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analyses/{analysis_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Analysis */
        get: operations["get_analysis_api_v1_analyses__analysis_id__get"];
        put?: never;
        post?: never;
        /** Delete Analysis */
        delete: operations["delete_analysis_api_v1_analyses__analysis_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analyses/{analysis_id}/transcript": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Transcript */
        get: operations["get_transcript_api_v1_analyses__analysis_id__transcript_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analyses/{analysis_id}/waveform": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Waveform */
        get: operations["get_waveform_api_v1_analyses__analysis_id__waveform_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analyses/{analysis_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Analysis */
        post: operations["retry_analysis_api_v1_analyses__analysis_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analyses/{analysis_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Analysis Events */
        get: operations["analysis_events_api_v1_analyses__analysis_id__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analyses/{analysis_id}/recommendations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Recommendations */
        get: operations["get_recommendations_api_v1_analyses__analysis_id__recommendations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Templates */
        get: operations["list_templates_api_v1_templates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/styles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Styles */
        get: operations["list_styles_api_v1_styles_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/shorts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Short */
        post: operations["create_short_api_v1_shorts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/shorts/{short_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Short */
        get: operations["get_short_api_v1_shorts__short_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/shorts/{short_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Short */
        post: operations["retry_short_api_v1_shorts__short_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/shorts/{short_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Short Events */
        get: operations["short_events_api_v1_shorts__short_id__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/shorts/{short_id}/files/{kind}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get File
         * @description Range requests are supported (video seeking).
         */
        get: operations["get_file_api_v1_shorts__short_id__files__kind__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/shorts/{short_id}/edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Edit */
        get: operations["get_edit_api_v1_shorts__short_id__edit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Edit */
        patch: operations["patch_edit_api_v1_shorts__short_id__edit_patch"];
        trace?: never;
    };
    "/api/v1/shorts/{short_id}/cut-suggestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cut Suggestions */
        post: operations["cut_suggestions_api_v1_shorts__short_id__cut_suggestions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AddNarration */
        AddNarration: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "add_narration";
            /** Text */
            text: string;
            /** Anchor Line Id */
            anchor_line_id: string;
        };
        /** AnalysisCreate */
        AnalysisCreate: {
            /** Url */
            url: string;
            /**
             * Template Id
             * @default celeb_item
             */
            template_id: string;
        };
        /** AnalysisList */
        AnalysisList: {
            /** Items */
            items: components["schemas"]["AnalysisOut"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** AnalysisOut */
        AnalysisOut: {
            /** Id */
            id: string;
            /** Video Id */
            video_id: string;
            /** Url */
            url: string;
            /** Template Id */
            template_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "fetching" | "transcribing" | "analyzing" | "ready" | "failed";
            /** Stage */
            stage: string | null;
            /** Progress */
            progress: number;
            /** Transcript Source */
            transcript_source: string | null;
            /** Warnings */
            warnings: string[];
            error: components["schemas"]["ErrorInfo"] | null;
            /** Retry Count */
            retry_count: number;
            /** Source */
            source: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finished At */
            finished_at: string | null;
        };
        /** ApplySuggestions */
        ApplySuggestions: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "apply_suggestions";
            /** Suggestion Ids */
            suggestion_ids: string[];
        };
        /** CutResult */
        CutResult: {
            /** Version */
            version: number;
            /** Suggestions */
            suggestions: components["schemas"]["Suggestion"][];
        };
        /** DeleteWords */
        DeleteWords: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "delete_words" | "restore_words";
            /** Word Ids */
            word_ids: string[];
        };
        /** EditDoc */
        EditDoc: {
            /**
             * Version
             * @default 1
             */
            version: number;
            title: components["schemas"]["Title"];
            /** Lines */
            lines: (components["schemas"]["SpeechLine"] | components["schemas"]["NarrationLine"])[];
            style: components["schemas"]["Style"];
            /**
             * Pending Suggestions
             * @default []
             */
            pending_suggestions: components["schemas"]["Suggestion"][];
        };
        /** EditOut */
        EditOut: {
            edit: components["schemas"]["EditDoc"];
            /** Duration Sec */
            duration_sec: number;
            /** Out Start Sec */
            out_start_sec: number;
        };
        /** EditPatch */
        EditPatch: {
            /** Base Version */
            base_version: number;
            /** Ops */
            ops: (components["schemas"]["DeleteWords"] | components["schemas"]["LineOp"] | components["schemas"]["RestoreAll"] | components["schemas"]["SetDisplayText"] | components["schemas"]["SplitLine"] | components["schemas"]["SetWordText"] | components["schemas"]["SetTitle"] | components["schemas"]["SetNarration"] | components["schemas"]["AddNarration"] | components["schemas"]["ApplySuggestions"] | components["schemas"]["SetStyle"])[];
        };
        /** EditResult */
        EditResult: {
            /** Version */
            version: number;
            /** Duration Sec */
            duration_sec: number;
            /** Preview Status */
            preview_status: string;
        };
        /** ErrorInfo */
        ErrorInfo: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** FillerRequest */
        FillerRequest: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "filler";
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** LineOp */
        LineOp: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "delete_line" | "delete_narration" | "restore_line";
            /** Line Id */
            line_id: string;
        };
        /** NarrationLine */
        NarrationLine: {
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "narration";
            /** Text */
            text: string;
            /** Anchor Line Id */
            anchor_line_id: string;
            /** Audio Path */
            audio_path: string;
            /** Audio Sec */
            audio_sec: number;
            /**
             * Voice Id
             * @default default
             */
            voice_id: string;
        };
        /** Product */
        Product: {
            /** Product */
            product: string;
            /** Brand */
            brand: string | null;
            /** Category */
            category: string;
        };
        /** Recommendation */
        Recommendation: {
            /** Rank */
            rank: number;
            /** Start Sec */
            start_sec: number;
            /** End Sec */
            end_sec: number;
            /** Duration Sec */
            duration_sec: number;
            /** Score */
            score: number;
            /** Signals */
            signals: {
                [key: string]: number;
            };
            /** Tags */
            tags: string[];
            /** Tag Labels */
            tag_labels: string[];
            /** Products */
            products: components["schemas"]["Product"][];
            /** Preview */
            preview: string;
        };
        /** RecommendationList */
        RecommendationList: {
            /** Scorer Version */
            scorer_version: string;
            /** Items */
            items: components["schemas"]["Recommendation"][];
        };
        /** RestoreAll */
        RestoreAll: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "restore_all";
        };
        /** Sentence */
        Sentence: {
            /** Id */
            id: string;
            /** Start Sec */
            start_sec: number;
            /** End Sec */
            end_sec: number;
            /** Text */
            text: string;
        };
        /** SetDisplayText */
        SetDisplayText: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "set_display_text";
            /** Line Id */
            line_id: string;
            /** Text */
            text?: string | null;
        };
        /** SetNarration */
        SetNarration: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "set_narration";
            /** Line Id */
            line_id: string;
            /** Text */
            text: string;
            /** Anchor Line Id */
            anchor_line_id?: string | null;
        };
        /** SetStyle */
        SetStyle: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "set_style";
            /** Preset Id */
            preset_id: string;
            /**
             * Overrides
             * @default {}
             */
            overrides: {
                [key: string]: unknown;
            };
        };
        /** SetTitle */
        SetTitle: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "set_title";
            /** Text */
            text: string;
            /**
             * Visible
             * @default true
             */
            visible: boolean;
        };
        /** SetWordText */
        SetWordText: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "set_word_text";
            /** Word Id */
            word_id: string;
            /** Text */
            text: string;
        };
        /** ShortCreate */
        ShortCreate: {
            /** Analysis Id */
            analysis_id: string;
            /**
             * Template Id
             * @default celeb_item
             */
            template_id: string;
            /** Start Sec */
            start_sec: number;
            /** End Sec */
            end_sec: number;
            /** Recommendation Rank */
            recommendation_rank?: number | null;
        };
        /** ShortOut */
        ShortOut: {
            /** Id */
            id: string;
            /** Analysis Id */
            analysis_id: string;
            /** Template Id */
            template_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "downloading" | "preparing" | "editing" | "rendering" | "done" | "failed";
            /** Stage */
            stage: string | null;
            /** Progress */
            progress: number;
            /** Start Sec */
            start_sec: number;
            /** End Sec */
            end_sec: number;
            /** Edit Version */
            edit_version: number;
            /** Preview Version */
            preview_version: number;
            /** Preview Status */
            preview_status: string;
            /** Warnings */
            warnings: string[];
            error: components["schemas"]["ErrorInfo"] | null;
            /** Retry Count */
            retry_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Exported At */
            exported_at: string | null;
        };
        /** SilenceRequest */
        SilenceRequest: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "silence";
            /**
             * Min Gap Sec
             * @default 0.5
             */
            min_gap_sec: number;
        };
        /** SpeechLine */
        SpeechLine: {
            /** Id */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "speech";
            /**
             * Deleted
             * @default false
             */
            deleted: boolean;
            /** Text */
            text: string;
            /** Display Text */
            display_text?: string | null;
            /** Words */
            words: components["schemas"]["Word"][];
        };
        /** SplitLine */
        SplitLine: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "split_line";
            /** Line Id */
            line_id: string;
            /** Word Id */
            word_id: string;
        };
        /** Style */
        Style: {
            /** Preset Id */
            preset_id: string;
            /**
             * Overrides
             * @default {}
             */
            overrides: {
                [key: string]: unknown;
            };
        };
        /** StylePreset */
        StylePreset: {
            /** Id */
            id: string;
            /** Values */
            values: {
                [key: string]: unknown;
            };
        };
        /** Suggestion */
        Suggestion: {
            /** Id */
            id: string;
            /** Type */
            type: string;
            /** Word Ids */
            word_ids: string[];
            /** Reason */
            reason: string;
        };
        /** Template */
        Template: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Description */
            description: string;
            /** Available */
            available: boolean;
        };
        /** Title */
        Title: {
            /** Text */
            text: string;
            /**
             * Visible
             * @default true
             */
            visible: boolean;
        };
        /** TranscriptOut */
        TranscriptOut: {
            /** Source */
            source: string;
            /** Sentences */
            sentences: components["schemas"]["Sentence"][];
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** WaveformOut */
        WaveformOut: {
            /** Duration Sec */
            duration_sec: number;
            /** Peaks Per Sec */
            peaks_per_sec: number;
            /** Peaks */
            peaks: number[];
        };
        /** Word */
        Word: {
            /** Id */
            id: string;
            /** Text */
            text: string;
            /** Raw Text */
            raw_text?: string | null;
            /** Start Sec */
            start_sec: number;
            /** End Sec */
            end_sec: number;
            /**
             * Deleted
             * @default false
             */
            deleted: boolean;
            /**
             * Trim Gap After
             * @default false
             */
            trim_gap_after: boolean;
            /**
             * Emphasis
             * @default false
             */
            emphasis: boolean;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    list_analyses_api_v1_analyses_get: {
        parameters: {
            query?: {
                status?: ("queued" | "fetching" | "transcribing" | "analyzing" | "ready" | "failed") | null;
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisList"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_analysis_api_v1_analyses_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnalysisCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_analysis_api_v1_analyses__analysis_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_analysis_api_v1_analyses__analysis_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_transcript_api_v1_analyses__analysis_id__transcript_get: {
        parameters: {
            query?: {
                start_sec?: number | null;
                end_sec?: number | null;
            };
            header?: never;
            path: {
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TranscriptOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_waveform_api_v1_analyses__analysis_id__waveform_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WaveformOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_analysis_api_v1_analyses__analysis_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    analysis_events_api_v1_analyses__analysis_id__events_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_recommendations_api_v1_analyses__analysis_id__recommendations_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecommendationList"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_templates_api_v1_templates_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Template"][];
                };
            };
        };
    };
    list_styles_api_v1_styles_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StylePreset"][];
                };
            };
        };
    };
    create_short_api_v1_shorts_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ShortCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShortOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_short_api_v1_shorts__short_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                short_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShortOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_short_api_v1_shorts__short_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                short_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShortOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    short_events_api_v1_shorts__short_id__events_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                short_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_file_api_v1_shorts__short_id__files__kind__get: {
        parameters: {
            query?: {
                download?: boolean;
            };
            header?: never;
            path: {
                short_id: string;
                kind: "preview" | "video" | "srt" | "thumbnail";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_edit_api_v1_shorts__short_id__edit_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                short_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EditOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_edit_api_v1_shorts__short_id__edit_patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                short_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EditPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EditResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cut_suggestions_api_v1_shorts__short_id__cut_suggestions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                short_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SilenceRequest"] | components["schemas"]["FillerRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CutResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
