declare module "transformers.js" {
  export function pipeline(
    task: PipelineType,
    model: string,
    { progress_callback }: { progress_callback?: Function }
  ): Promise<ZeroShotClassificationPipeline>;
  export type PipelineType = "zero-shot-classification";
  export type ZeroShotClassificationOutput = {
    labels: string[];
    scores: number[];
    sequence: string;
  };
  export type ZeroShotClassificationPipeline = any;
}
