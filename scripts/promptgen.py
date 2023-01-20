import html
import os
import time

import torch
import transformers

from modules import shared, generation_parameters_copypaste

from modules import scripts, script_callbacks, devices, ui
import gradio as gr

from modules.ui_components import FormRow


class Model:
    name = None
    model = None
    tokenizer = None


available_models = []
current = Model()

base_dir = scripts.basedir()
models_dir = os.path.join(base_dir, "models")


def device():
    return devices.cpu if shared.opts.promptgen_device == 'cpu' else devices.device


def list_available_models():
    available_models.clear()

    os.makedirs(models_dir, exist_ok=True)

    for dirname in os.listdir(models_dir):
        if os.path.isdir(os.path.join(models_dir, dirname)):
            available_models.append(dirname)

    for name in [x.strip() for x in shared.opts.promptgen_names.split(",")]:
        if not name:
            continue

        available_models.append(name)


def get_model_path(name):
    dirname = os.path.join(models_dir, name)
    if not os.path.isdir(dirname):
        return name

    return dirname


def generate_batch(input_ids, min_length, max_length, num_beams, temperature, repetition_penalty, length_penalty, sampling_mode, top_k, top_p):
    top_p = float(top_p) if sampling_mode == 'Top P' else None
    top_k = int(top_k) if sampling_mode == 'Top K' else None

    outputs = current.model.generate(
        input_ids,
        do_sample=True,
        temperature=max(float(temperature), 1e-6),
        repetition_penalty=repetition_penalty,
        length_penalty=length_penalty,
        top_p=top_p,
        top_k=top_k,
        num_beams=int(num_beams),
        min_length=min_length,
        max_length=max_length,
        pad_token_id=current.tokenizer.pad_token_id or current.tokenizer.eos_token_id
    )
    texts = current.tokenizer.batch_decode(outputs, skip_special_tokens=True)
    return texts


def model_selection_changed(model_name):
    if model_name == "None":
        current.tokenizer = None
        current.model = None
        current.name = None

        devices.torch_gc()


def generate(id_task, model_name, batch_count, batch_size, text, *args):
    shared.state.textinfo = "Loading model..."
    shared.state.job_count = batch_count

    if current.name != model_name:
        current.tokenizer = None
        current.model = None
        current.name = None

        if model_name != 'None':
            path = get_model_path(model_name)
            current.tokenizer = transformers.AutoTokenizer.from_pretrained(path)
            current.model = transformers.AutoModelForCausalLM.from_pretrained(path)
            current.name = model_name

    assert current.model, 'No model available'
    assert current.tokenizer, 'No tokenizer available'

    current.model.to(device())

    shared.state.textinfo = ""

    input_ids = current.tokenizer(text, return_tensors="pt").input_ids
    if input_ids.shape[1] == 0:
        input_ids = torch.asarray([[current.tokenizer.bos_token_id]], dtype=torch.long)
    input_ids = input_ids.to(device())
    input_ids = input_ids.repeat((batch_size, 1))

    markup = '<table><tbody>'

    index = 0
    for i in range(batch_count):
        texts = generate_batch(input_ids, *args)
        shared.state.nextjob()
        for generated_text in texts:
            index += 1
            markup += f"""
<tr>
<td>
<div class="prompt gr-box gr-text-input">
    <p id='promptgen_res_{index}'>{html.escape(generated_text)}</p>
</div>
</td>
<td class="sendto">
    <a class='gr-button gr-button-lg gr-button-secondary' onclick="promptgen_send_to_txt2img(gradioApp().getElementById('promptgen_res_{index}').textContent)">to txt2img</a>
    <a class='gr-button gr-button-lg gr-button-secondary' onclick="promptgen_send_to_img2img(gradioApp().getElementById('promptgen_res_{index}').textContent)">to img2img</a>
</td>
</tr>
"""

    markup += '</tbody></table>'

    return markup, ''


def find_prompts(fields):
    field_prompt = [x for x in fields if x[1] == "Prompt"][0]
    field_negative_prompt = [x for x in fields if x[1] == "Negative prompt"][0]
    return [field_prompt[0], field_negative_prompt[0]]


def send_prompts(text):
    params = generation_parameters_copypaste.parse_generation_parameters(text)
    negative_prompt = params.get("Negative prompt", "")
    return params.get("Prompt", ""), negative_prompt or gr.update()


def add_tab():
    list_available_models()

    with gr.Blocks(analytics_enabled=False) as tab:
        with gr.Row():
            with gr.Column(scale=80):
                prompt = gr.Textbox(label="Prompt", elem_id="promptgen_prompt", show_label=False, lines=2, placeholder="Beginning of the prompt (press Ctrl+Enter or Alt+Enter to generate)").style(container=False)
            with gr.Column(scale=10):
                submit = gr.Button('Generate', elem_id="promptgen_generate", variant='primary')

        with gr.Row(elem_id="promptgen_main"):
            with gr.Column(variant="compact"):
                selected_text = gr.TextArea(elem_id='promptgen_selected_text', visible=False)
                send_to_txt2img = gr.Button(elem_id='promptgen_send_to_txt2img', visible=False)
                send_to_img2img = gr.Button(elem_id='promptgen_send_to_img2img', visible=False)

                with FormRow():
                    model_selection = gr.Dropdown(label="Model", elem_id="promptgen_model", value=available_models[0], choices=["None"] + available_models)

                with FormRow():
                    sampling_mode = gr.Radio(label="Sampling mode", elem_id="promptgen_sampling_mode", value="Top K", choices=["Top K", "Top P"])
                    top_k = gr.Slider(label="Top K", elem_id="promptgen_top_k", value=12, minimum=1, maximum=50, step=1)
                    top_p = gr.Slider(label="Top P", elem_id="promptgen_top_p", value=0.15, minimum=0, maximum=1, step=0.001)

                with gr.Row():
                    num_beams = gr.Slider(label="Number of beams", elem_id="promptgen_num_beams", value=1, minimum=1, maximum=8, step=1)
                    temperature = gr.Slider(label="Temperature", elem_id="promptgen_temperature", value=1, minimum=0, maximum=4, step=0.01)
                    repetition_penalty = gr.Slider(label="Repetition penalty", elem_id="promptgen_repetition_penalty", value=1, minimum=1, maximum=4, step=0.01)

                with FormRow():
                    length_penalty = gr.Slider(label="Length preference", elem_id="promptgen_length_preference", value=1, minimum=-10, maximum=10, step=0.1)
                    min_length = gr.Slider(label="Min length", elem_id="promptgen_min_length", value=20, minimum=1, maximum=400, step=1)
                    max_length = gr.Slider(label="Max length", elem_id="promptgen_max_length", value=150, minimum=1, maximum=400, step=1)

                with FormRow():
                    batch_count = gr.Slider(label="Batch count", elem_id="promptgen_batch_count", value=1, minimum=1, maximum=100, step=1)
                    batch_size = gr.Slider(label="Batch size", elem_id="promptgen_batch_size", value=10, minimum=1, maximum=100, step=1)

                with open(os.path.join(base_dir, "explanation.html"), encoding="utf8") as file:
                    footer = file.read()
                    gr.HTML(footer)

            with gr.Column():
                with gr.Group(elem_id="promptgen_results_column"):
                    res = gr.HTML()
                    res_info = gr.HTML()

        submit.click(
            fn=ui.wrap_gradio_gpu_call(generate, extra_outputs=['']),
            _js="submit_promptgen",
            inputs=[model_selection, model_selection, batch_count, batch_size, prompt, min_length, max_length, num_beams, temperature, repetition_penalty, length_penalty, sampling_mode, top_k, top_p, ],
            outputs=[res, res_info]
        )

        model_selection.change(
            fn=model_selection_changed,
            inputs=[model_selection],
            outputs=[],
        )

        send_to_txt2img.click(
            fn=send_prompts,
            inputs=[selected_text],
            outputs=find_prompts(ui.txt2img_paste_fields)
        )

        send_to_img2img.click(
            fn=send_prompts,
            inputs=[selected_text],
            outputs=find_prompts(ui.img2img_paste_fields)
        )

    return [(tab, "Promptgen", "promptgen")]


def on_ui_settings():
    section = ("promptgen", "Promptgen")

    shared.opts.add_option("promptgen_names", shared.OptionInfo("AUTOMATIC/promptgen-lexart, AUTOMATIC/promptgen-majinai-safe, AUTOMATIC/promptgen-majinai-unsafe", "Hugginface model names for promptgen, separated by comma", section=section))
    shared.opts.add_option("promptgen_device", shared.OptionInfo("gpu", "Device to use for text generation", gr.Radio, {"choices": ["gpu", "cpu"]}, section=section))


def on_unload():
    current.model = None
    current.tokenizer = None


script_callbacks.on_ui_tabs(add_tab)
script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_script_unloaded(on_unload)
